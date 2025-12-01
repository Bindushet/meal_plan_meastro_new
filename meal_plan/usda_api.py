import os
from dotenv import load_dotenv
import requests

load_dotenv()

# ===== STEP: ADD YOUR API KEY HERE =====
USDA_API_KEY = os.getenv("USDA_API_KEY")  # replace with your key
# ======================================

BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

def get_ingredient_nutrition(ingredient_name, qty_in_grams=100):
    params = {
        "api_key": USDA_API_KEY,
        "query": ingredient_name,
        "pageSize": 1
    }

    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        print("USDA API error:", response.status_code)
        return {}

    data = response.json()
    foods = data.get("foods")
    if not foods:
        return {}

    food = foods[0]
    nutrients = {}

    for n in food.get("foodNutrients", []):

        name = n.get("nutrientName")
        value = n.get("value")
        unit = n.get("unitName")

        if not name or value is None:
            continue

        # Convert to numeric
        try:
            value = float(value)
        except:
            continue

        # Scale by qty
        scaled = round(value * qty_in_grams / 100, 2)

        nutrients[name] = {"value": scaled, "unit": unit}

    return nutrients
