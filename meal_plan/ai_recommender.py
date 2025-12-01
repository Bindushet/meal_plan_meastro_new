# meal_plan/ai_recommender.py
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import pulp

# ------------------- Dietary Restriction Ingredient Avoidance List -------------------

DIETARY_RESTRICTIONS = {
    "vegan": [
        "meat", "bacon","chicken", "fish", "seafood", "egg", "milk", "cheese", "butter","beef","ham",
        "yogurt", "cream", "honey", "gelatin", "lard", "casein", "whey","bone","boneless","shrimp","pork","duck"
    ],
    "vegetarian": [
        "meat", "bacon","chicken", "fish", "seafood", "gelatin", "lard","beef","ham","bone","boneless","shrimp","pork","duck"
    ],
    "lacto_vegetarian": [
        "meat", "chicken","bacon", "fish", "seafood", "egg", "gelatin","beef","ham","bone","boneless","shrimp","duck"
    ],
    "ovo_vegetarian": [
        "meat", "chicken","bacon", "fish", "seafood", "milk", "cheese", "butter", "cream","beef","ham","bone","boneless","shrimp","duck"
    ],
    "pescatarian": [
        "meat", "bacon", "chicken", "pork", "beef", "lamb", "duck","ham","bone","boneless"
    ],
    "gluten-free": [
        "wheat", "barley", "rye", "malt", "triticale", "semolina", "spelt", "farro", "couscous","breadcrumbs", "soy_sauce", "beer", "durum"
    ],
    "keto": [
        "sugar", "honey", "rice", "pasta","oats", "wheat", "corn", "potato", "beans", "lentil", "banana", "mango", "bread","high_carb_fruits"
    ],
    "paleo": [
        "grains", "beans", "lentil", "soy", "peanut", "dairy", "sugar", "vegetable oil""processed_food","wheat", "rice", "corn","cheese", "milk"
    ],
    "low-carb": [
        "sugar", "bread", "pasta", "rice", "potato", "sweet", "honey", "syrup", "corn",
    ],
    "low-fat": [
        "butter", "oil", "cream", "fatty", "fried", "mayonnaise","fatty_meat"
    ],
    "low-sodium": [
        "salt", "bacon", "soy sauce", "processed", "cured", "pickle", "bouillon","ham", "salted_butter", "chips"
    ],
    "dairy-free": [
        "milk", "cheese", "butter", "yogurt", "cream", "ghee", "whey", "casein"
    ],
    "nut-free": [
        "almond", "walnut", "cashew", "hazelnut", "pistachio", "peanut", "pecan"
    ],
    "soy-free": [
        "soy", "tofu", "tempeh", "soy sauce", "edamame", "miso"
    ],
    "egg-free": [
        "egg", "mayonnaise", "meringue"
    ],
    "shellfish-free": [
        "shrimp", "crab", "lobster", "clam", "oyster", "scallop", "mussel"
    ],
    "fish-free": [
        "fish", "salmon", "tuna", "cod", "anchovy", "sardine","shrimp"
    ],
    "halal": [
        "pork", "bacon", "ham", "alcohol", "beer", "wine", "non-halal","gelatin", "lard"
    ],
    "kosher": [
        "pork", "bacon","shellfish", "bacon", "non-kosher", "meat and dairy","shrimp", "lobster","cheese_with_rennet"
    ],
}
def classify_meal_by_calories(cal):
    """
    Simple nutrition-based meal classification based on calories.
    Adjust thresholds as needed.
    """
    try:
        cal = float(cal)
    except:
        return "Unknown"

    if cal < 200:
        return "Snack"
    elif cal < 400:
        return "Breakfast"
    elif cal < 700:
        return "Lunch"
    else:
        return "Dinner"


AI_DATA_PATH = os.path.join(os.path.dirname(__file__), "ai_data.pkl")

try:
    ART = joblib.load(AI_DATA_PATH)
    VECTORIZER = ART["vectorizer"]
    TFIDF_MATRIX = ART["tfidf_matrix"]
    DF_RECIPES = ART["df"]

    # ✅ Rename columns so Django templates can access them easily
    DF_RECIPES.columns = [c.replace(" ", "_") for c in DF_RECIPES.columns]
    print("🧾 Columns in DF_RECIPES:", DF_RECIPES.columns.tolist())

    # 🔥 Remove all bad recipes with 'Food.com' placeholder instructions
    if "RecipeInstructions_cleaned" in DF_RECIPES.columns:
        DF_RECIPES = DF_RECIPES[
            ~DF_RECIPES["RecipeInstructions_cleaned"]
                .astype(str)
                .str.lower()
                .str.contains("food.com", na=False)
        ].copy()
        print("🚫 Removed Food.com placeholder recipes. Remaining:", len(DF_RECIPES))
        # Add meal type classification column
        if DF_RECIPES is not None:
            DF_RECIPES["MealType"] = DF_RECIPES["Calories"].apply(classify_meal_by_calories)

    else:
        print("⚠️ No RecipeInstructions column — skipping filter.")

    print("✅ AI model loaded successfully.")
except Exception as e:
    print("⚠️ Failed to load ai_data.pkl:", e)
    DF_RECIPES = None


def recommend_by_pantry(pantry_list, top_k=10):
    if DF_RECIPES is None:
        raise ValueError("ai_data.pkl not found or invalid.")
    pantry_text = " ".join([p.lower() for p in pantry_list])
    q_vec = VECTORIZER.transform([pantry_text])
    sims = cosine_similarity(q_vec, TFIDF_MATRIX).flatten()
    idx = np.argsort(-sims)[:top_k]
    results = DF_RECIPES.iloc[idx].copy()
    results["match_score"] = sims[idx]
    return results.reset_index(drop=True)


def personalize_results(df_results, user):
    profile = getattr(user, "profile", None)
    if not profile:
        return df_results
    res = df_results.copy()

    if profile.allergy_info:
        allergies = [a.strip().lower() for a in profile.allergy_info.split(",")]
        res = res[~res["RecipeIngredientParts_cleaned"].str.lower().apply(
            lambda s: any(a in s for a in allergies)
        )]


    # --- 2️⃣ Dietary Restriction Filtering (by ingredient exclusion) ---
    dietary_pref = (profile.dietary_pref or "").strip().lower()
    if dietary_pref and dietary_pref != "none":
        avoid_list = DIETARY_RESTRICTIONS.get(dietary_pref, [])
        if avoid_list:
            avoid_pattern = "|".join([f"\\b{a}\\b" for a in avoid_list])
            res = res[~res["RecipeIngredientParts_cleaned"].str.lower().str.contains(avoid_pattern, na=False)]


    if profile.goal.lower() == "weight loss":
        res = res.sort_values(["match_score", "Calories"], ascending=[False, True])
    elif profile.goal.lower() == "weight gain":
        res = res.sort_values(["match_score", "Calories"], ascending=[False, False])
    else:
        res = res.sort_values("match_score", ascending=False)
    return res.reset_index(drop=True)

# -------------------------------
# FILTER BY PANTRY + EXCLUDE SAVED
# -------------------------------
def filter_recipes_by_pantry_ingredients(df, pantry_list, saved_recipe_names=None, max_extra=3):
    """
    Filter recipes by pantry ingredients + exclude user-saved recipes.
    """
    pantry_set = set(p.lower() for p in pantry_list)
    saved_recipe_names = set(n.lower() for n in saved_recipe_names) if saved_recipe_names else set()

    filtered_rows = []

    for idx, row in df.iterrows():

        # Exclude recipes user already generated/saved
        if row["Name"].lower() in saved_recipe_names:
            continue

        recipe_ings = row["RecipeIngredientParts_cleaned"]
        if not isinstance(recipe_ings, str):
            continue

        recipe_set = set(i.strip().lower() for i in recipe_ings.split(",") if i.strip())

        # require all pantry ingredients
        if not pantry_set.issubset(recipe_set):
            continue

        # allow only a few extra ingredients
        extra_count = len(recipe_set - pantry_set)
        if extra_count <= max_extra:
            filtered_rows.append(idx)

    return df.loc[filtered_rows].copy()

def filter_by_serving_size(df, serving_size, tolerance=1):
    """
    Keep recipes whose serving size is within (serving_size ± tolerance).
    Uses 'RecipeServings' column from your dataset.
    """
    if "RecipeServings" not in df.columns:
        return df   # skip if column missing

    df = df.copy()

    # Convert servings into float safely
    def parse_serv(v):
        try:
            return float(v)
        except:
            return None

    df["Servings_clean"] = df["RecipeServings"].apply(parse_serv)

    lower = serving_size - tolerance
    upper = serving_size + tolerance

    return df[df["Servings_clean"].between(lower, upper, inclusive="both")]


def generate_ai_meal(user, pantry_items, top_k=10,exclude_names=None,serving_size=None,meal_type=None):
    exclude_names = set(n.lower() for n in exclude_names) if exclude_names else set()
    pantry_names = [p.ingredient_name for p in pantry_items]
    recs = recommend_by_pantry(pantry_names, top_k=50)
    # Step 2: Strict ingredient matching (your new logic)
    recs = filter_recipes_by_pantry_ingredients(recs, pantry_names, max_extra=3)

    # Step 3: NEW – Remove recipes already saved by the user
    if exclude_names:
        recs = recs[~recs["Name"].str.lower().isin(exclude_names)]
        

    # If too few recipes remain, fall back to similarity only
    if len(recs) < top_k:
        recs = recommend_by_pantry(pantry_names, top_k)

        # remove saved recipes again
        if exclude_names:
            recs = recs[~recs["Name"].str.lower().isin(exclude_names)]


    recs = personalize_results(recs, user)
    # ---- SERVING SIZE FILTERING ----
    if serving_size:
        recs = filter_by_serving_size(recs, serving_size, tolerance=4)

    # Add automatic meal classification
    recs["MealType"] = recs["Calories"].apply(classify_meal_by_calories)   
    
    return recs.head(top_k)



def generate_meal_plan(
    user,
    pantry_items,
    days=1,
    meals_per_day=3,
    exclude_names=None,
    serving_size=None):

    exclude_names = set(n.lower() for n in exclude_names) if exclude_names else set()
    pantry_names = [p.ingredient_name for p in pantry_items]

    # Pantry → similarity search
    recs = recommend_by_pantry(pantry_names, top_k=80)
    recs = filter_recipes_by_pantry_ingredients(recs, pantry_names, max_extra=3)
    if exclude_names:
        recs = recs[~recs["Name"].str.lower().isin(exclude_names)]
    if len(recs) < meals_per_day * days:
        recs = recommend_by_pantry(pantry_names, top_k=80)
        if exclude_names:
            recs = recs[~recs["Name"].str.lower().isin(exclude_names)]

    print(recs.columns)
    recs = personalize_results(recs, user)
    if serving_size:
        recs = filter_by_serving_size(recs, serving_size, tolerance=4)

    recs["MealType"] = recs["Calories"].apply(classify_meal_by_calories)

    df = recs.copy()
    df = df[df["Calories"] > 0].copy()

    # Calorie target calculation
    try:
        weight = float(user.profile.weight_kg or 70)
        height = float(user.profile.height_cm or 170)
        age = float(user.profile.age or 25)
        goal = user.profile.goal.lower()
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
        if goal == "weight loss":
            target = bmr - 400
        elif goal == "weight gain":
            target = bmr + 400
        else:
            target = bmr
    except Exception:
        target = 2000

    # -------- Optimization --------
    n = len(df)
    prob = pulp.LpProblem("MealPlan", pulp.LpMinimize)

    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]
    cal = df["Calories"].values
    total_cal = pulp.lpSum(x[i] * cal[i] for i in range(n))

    # linear deviation objective (instead of quadratic)
    deviation = pulp.LpVariable("deviation", lowBound=0)
    prob += deviation  # minimize deviation

    # absolute deviation constraints
    prob += total_cal - deviation <= target * days
    prob += total_cal + deviation >= target * days

    # exact count of meals
    prob += pulp.lpSum(x) == meals_per_day * days

    # meal-type constraints (at least one of each per day)
    prob += pulp.lpSum(x[i] for i in range(n) if df.iloc[i]["MealType"] == "Breakfast") >= days
    prob += pulp.lpSum(x[i] for i in range(n) if df.iloc[i]["MealType"] == "Lunch") >= days
    prob += pulp.lpSum(x[i] for i in range(n) if df.iloc[i]["MealType"] == "Dinner") >= days
    
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    chosen = [i for i in range(n) if pulp.value(x[i]) == 1]

    plan = df.iloc[chosen].copy()
    plan["TotalCalories"] = plan["Calories"].sum()

    return plan.reset_index(drop=True)
