# 🥗 Protein Scanner

Protein Scanner is a lightweight FastAPI web application that uses **Google Gemini** vision capabilities to identify food items on a plate, estimate their weight in grams, and query the **USDA FoodData Central API** to calculate the total protein content.

---

## ✨ Features

* **AI-Powered Plate Analysis:** Uses Google Gemini to detect distinct food items from food photographs and estimate portion sizes in grams.
* **USDA Database Integration:** Automatically searches the USDA nutrition database to fetch accurate protein metrics per 100g for each identified item.
* **Aggregated Breakdown:** Computes individual item protein counts and sums them up for a total meal protein score.
* **Static Asset Support:** Serves a frontend interface directly from a local `static/` directory.

---

## 🛠️ Tech Stack

* **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **AI Vision Model:** [Google GenAI SDK](https://github.com/google/genai) (`gemini-3.8-flash` by default)
* **HTTP Client:** [Httpx](https://www.python-httpx.org/)
* **External API:** USDA FoodData Central API
* **Environment Management:** python-dotenv

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.9 or higher
* A **Google Gemini API Key**
* A **USDA FoodData Central API Key** (You can sign up for a free key at [USDA FDC API](https://fdc.nal.usda.gov/api-key-signup.html))

### 2. Clone and Setup Environment

Create a project directory, add your code to a file named `main.py`, and create a `static/` folder with your frontend `index.html`.

Install the required dependencies:

```bash
pip install fastapi uvicorn httpx python-dotenv google-genai
