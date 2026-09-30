Amino Plate App — protein scanner 

Upload or photograph a plate of food. Gemini's free-tier vision model identifies each item and estimates its weight; USDA FoodData Central supplies protein-per-100g for each item; the app totals the protein on the plate. 

How it works:
you submit a photo.
Gemini (vision) returns a list of food items with estimated grams.
Each item is looked up in USDA FoodData Central to get protein per 100 g.
The backend multiplies and sums to give total protein, and the frontend displays an itemized breakdown.
