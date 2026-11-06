import asyncio
import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USDA_API_KEY = os.getenv("USDA_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in your .env file")
if not USDA_API_KEY:
    raise RuntimeError("Set USDA_API_KEY in your .env file")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Protein Scanner")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

VISION_PROMPT = """You are looking at a photo of a plate of food. Identify every \
distinct food item on the plate and estimate its weight in grams, using the \
plate, cutlery, and other objects in frame as a scale reference.

Respond with ONLY a JSON object (no markdown fences, no commentary) in this \
exact shape:

{
  "items": [
    {"name": "grilled chicken breast", "grams": 150, "search_term": "chicken breast, grilled"},
    {"name": "steamed broccoli", "grams": 80, "search_term": "broccoli, cooked"}
  ],
  "confidence_note": "one short sentence on portion-estimate confidence"
}

Rules:
- "search_term" should be a plain, generic USDA-style food description (no brand names, no cooking-adjective stacking) so it can be looked up in a nutrition database.
- Only include items that are actually food (skip garnish that's purely decorative, like a lemon wedge that won't be eaten, unless it's substantial).
- Give your best numeric estimate for grams even if uncertain — never omit it.
"""


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


import time

async def identify_foods(image_bytes: bytes, media_type: str) -> dict:
    models_to_try = list(dict.fromkeys([GEMINI_MODEL, "gemini-3.8-flash", "gemini-3.1-flash-lite"]))
    deadline = time.monotonic() + 40  
    errors = []

    for model_name in models_to_try:
        for attempt in range(2):
            remaining = deadline - time.monotonic()
            if remaining < 5:
                break
            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model_name,
                        contents=[
                            VISION_PROMPT,
                            types.Part.from_bytes(data=image_bytes, mime_type=media_type),
                        ],
                    ),
                    timeout=min(remaining, 20),
                )
                return extract_json(response.text or "")
            except asyncio.TimeoutError:
                errors.append(f"{model_name}: timed out")
                break
            except Exception as exc:
                errors.append(f"{model_name}: {str(exc)[:120]}")
                code = getattr(exc, "code", None)
                if code in (500, 503) or isinstance(exc, json.JSONDecodeError):
                    await asyncio.sleep(1.5)
                    continue
                break

    raise HTTPException(
        status_code=503,
        detail="The AI model is busy right now. Please try again in a minute. "
        + " | ".join(errors[-3:]),
    )

async def lookup_protein_per_100g(search_term: str) -> tuple[float | None, str | None]:
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "query": search_term,
        "api_key": USDA_API_KEY,
        "pageSize": 5,
        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
    }
    async with httpx.AsyncClient(timeout=10) as http_client:
        try:
            resp = await http_client.get(url, params=params)
            if resp.status_code != 200:
                return None, None
            data = resp.json()
            foods = data.get("foods", [])
            if not foods:
                return None, None
            best = foods[0]
            for nutrient in best.get("foodNutrients", []):
                if nutrient.get("nutrientId") == 1003 or nutrient.get("nutrientName") == "Protein":
                    return nutrient.get("value"), best.get("description")
            return None, best.get("description")
        except Exception:
            return None, None


@app.post("/api/analyze")
async def analyze_plate(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Please upload a JPEG, PNG, or WEBP image")

    image_bytes = await file.read()
    vision_result = await identify_foods(image_bytes, file.content_type)
    vision_items = vision_result.get("items", [])

    tasks = [
        lookup_protein_per_100g(item.get("search_term", item["name"]))
        for item in vision_items
    ]
    usda_results = await asyncio.gather(*tasks)

    items = []
    total_protein = 0.0

    for item, (protein_per_100g, matched_name) in zip(vision_items, usda_results):
        grams = float(item.get("grams", 0))
        if protein_per_100g is not None:
            item_protein = round(protein_per_100g * grams / 100, 1)
            total_protein += item_protein
        else:
            item_protein = None

        items.append(
            {
                "name": item["name"],
                "grams": grams,
                "protein_g": item_protein,
                "matched_food": matched_name,
                "found_in_database": protein_per_100g is not None,
            }
        )

    return {
        "items": items,
        "total_protein_g": round(total_protein, 1),
        "confidence_note": vision_result.get("confidence_note"),
    }


@app.get("/")
async def index():
    path = STATIC_DIR / "index.html"
    if not path.exists():
        return {"error": "index.html not found in static folder"}
    return FileResponse(path)