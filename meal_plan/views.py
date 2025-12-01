from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User # Import User from auth
from django.contrib import messages
from .models import Profile ,PantryItem, Recipe, FavoriteRecipe, DayPlan
from .forms import PantryItemForm
from .ai_recommender import generate_ai_meal, generate_meal_plan
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .usda_api import get_ingredient_nutrition
import json
import requests
from datetime import date
from django.utils import timezone
from .utils import convert_to_grams, get_density, generate_recipe_image
import base64
from io import BytesIO

from django.core.files.base import ContentFile


def generate_food_image(name, ingredients, instructions):
    """Generate high-quality food images with Pollinations.ai"""
    # ingredients is already a single string, so no join is needed
    ingredients_text = str(ingredients)
    prompt = (
        f"High quality professional food photograph of {name}. "
        f"Ingredients: {ingredients_text}. Cooking instructions: {instructions}. "
        f"Restaurant style lighting, appetizing, DSLR photo, 4k."
    )
    encoded = requests.utils.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512"

# --------------------------
#  SAFE EXTRACTOR FUNCTION
# --------------------------
def extract_main_nutrients(nutrients):
    return {
        "Carbohydrates": nutrients.get("Carbohydrate, by difference", {}).get("value", 0),
        "Protein": nutrients.get("Protein", {}).get("value", 0),
        "Fat": nutrients.get("Total lipid (fat)", {}).get("value", 0),
        "Water": nutrients.get("Water", {}).get("value", 0),

        "Vitamins": {
            "Vitamin C": nutrients.get("Vitamin C, total ascorbic acid", {}).get("value", 0),
            "Vitamin B6": nutrients.get("Vitamin B-6", {}).get("value", 0),
            "Vitamin A": nutrients.get("Vitamin A, IU", {}).get("value", 0),
            "Vitamin K": nutrients.get("Vitamin K (phylloquinone)", {}).get("value", 0),
        },

        "Minerals": {
            "Calcium": nutrients.get("Calcium, Ca", {}).get("value", 0),
            "Iron": nutrients.get("Iron, Fe", {}).get("value", 0),
            "Potassium": nutrients.get("Potassium, K", {}).get("value", 0),
            "Magnesium": nutrients.get("Magnesium, Mg", {}).get("value", 0),
            "Sodium": nutrients.get("Sodium, Na", {}).get("value", 0),
        }
    }

# ---- Helper: Combine ingredients + quantities ----
def combine_ing_qty(parts, qtys):
    parts_list = [p.strip() for p in str(parts).split(",") if p.strip()]
    qty_list = [q.strip() for q in str(qtys).split(",") if q.strip()]

    combined = []
    for ing, qty in zip(parts_list, qty_list):
        combined.append(f"{ing}-{qty}")

    return combined



@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    items = PantryItem.objects.filter(user=request.user).order_by('-created_at')
    form = PantryItemForm()
    favorites = FavoriteRecipe.objects.filter(user=request.user).select_related('recipe')
    user_recipes = Recipe.objects.filter(user=request.user).order_by("-created_at")
    saved_dayplans = DayPlan.objects.filter(user=request.user).order_by('-date')
    day_favorites = DayPlan.objects.filter(user=request.user, is_favorite=True)

    # Ensure nutrition_info is a dict
    for r in user_recipes:
        if not r.nutrition_info:
            r.nutrition_info = {}
        elif isinstance(r.nutrition_info, str):
            # If stored as JSON string in DB
            try:
                r.nutrition_info = json.loads(r.nutrition_info)
            except:
                r.nutrition_info = {}
        if not r.main_nutrients:
            r.main_nutrients = extract_main_nutrients(r.nutrition_info)       

    # static session index for regenerate
    if 'recipe_index' not in request.session:
        request.session['recipe_index'] = 0

     # ✅ initialize context_recipe for safe default
    context_recipe = None    

    if request.method == 'POST':
        form = PantryItemForm(request.POST, request.FILES)
        if 'add_pantry_item' in request.POST:
            form = PantryItemForm(request.POST, request.FILES)
            if form.is_valid():
                pantry_item = form.save(commit=False)
                pantry_item.user = request.user

                try:
                    grams = convert_to_grams(
                        pantry_item.qty,
                        pantry_item.unit,
                        pantry_item.ingredient_name
                    )
                    pantry_item.nutrition_info = get_ingredient_nutrition(
                        pantry_item.ingredient_name,
                        grams
                    )
                except Exception as e:
                    print(f"⚠️ USDA API error for {pantry_item.ingredient_name}: {e}")
                    pantry_item.nutrition_info = {}
                pantry_item.save()
                messages.success(request, 'Pantry item added!')
                return redirect('dashboard')
            else:
                print(form.errors)

        elif 'first_name' in request.POST:
            # Profile update
            user = request.user
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()

            profile.age = request.POST.get('age') or None
            profile.gender = request.POST.get('gender', '')
            profile.height_cm = request.POST.get('height_cm') or None
            profile.weight_kg = request.POST.get('weight_kg') or None
            profile.goal = request.POST.get('goal', '')
            profile.dietary_pref = request.POST.get('dietary_pref', '')
            profile.allergy_info = request.POST.get('allergy_info', '')
            profile.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')
        
        elif 'generate_meal' in request.POST or 'regenerate' in request.POST:
            print("✅ Generate meal POST received")

            # --------------------------------------
            # NEW: Saved recipes → Exclude from AI
            # --------------------------------------
            saved_recipe_names = set(
                Recipe.objects.filter(user=request.user)
                .values_list("name", flat=True)
            )

            # -------------------------------
            # NEW: Regenerate uses session IDs
            # -------------------------------
            if 'regenerate' in request.POST:
                ids = request.session.get("last_selected_ingredients", [])
            else:
                ingredient_ids = request.POST.get("selected_ingredients", "")
                ids = [int(i) for i in ingredient_ids.split(",") if i.isdigit()]
                request.session["last_selected_ingredients"] = ids

            if not ids:
                messages.error(request, "Please select at least one ingredient.")
                return redirect("dashboard")

            pantry_items = PantryItem.objects.filter(id__in=ids)
            serving_size = int(request.POST.get("serving_size", 2))
            meal_type = request.POST.get("meal_type")
            # --------------------------------------------------------
            # 🔥 NEW: Pass saved recipe names into the AI generator
            # --------------------------------------------------------
            
            ai_recipes_df = generate_ai_meal(
                user=request.user,
                pantry_items=pantry_items,
                top_k=10,
                exclude_names=saved_recipe_names,     # <--- ✨ NEW
                serving_size=serving_size,
                meal_type=meal_type   # <--- NEW
            )

             # NEW: Filter by meal type if user selected one
            if meal_type:
                ai_recipes_df = ai_recipes_df[ai_recipes_df["MealType"] == meal_type]

            if len(ai_recipes_df) == 0:
                messages.error(request, "No recipes found.")
                return redirect("dashboard")

            # -----------------------
            # ROTATE recipe index
            # -----------------------
            index = request.session.get("recipe_index", 0)
            recipe = ai_recipes_df.iloc[index % len(ai_recipes_df)]
            request.session["ai_recipes"] = ai_recipes_df.to_dict(orient="records")
            request.session["recipe_index"] = (index + 1) % len(ai_recipes_df)

            # -----------------------
            # IMAGE CLEANUP
            # -----------------------
            img_field = recipe.Images
            if isinstance(img_field, list) and img_field:
                img_url = img_field[0]
            elif isinstance(img_field, str):
                img_field = img_field.strip("[]").replace("'", "").replace('"', '')
                img_urls = [u.strip() for u in img_field.split(",") if u.strip()]
                img_url = img_urls[0] if img_urls else ""
            else:
                img_url = ""

            # -----------------------
            # INGREDIENT + QTY COMBINE
            # -----------------------
            ingredients_with_qty = combine_ing_qty(
                getattr(recipe, "RecipeIngredientParts_cleaned", ""),
                getattr(recipe, "RecipeIngredientQuantities_cleaned", "")
            )

            # ---------------------------------------
            # 🔥 Generate AI Image (Name + Ingredients + Instructions)
            # ---------------------------------------

            sd_image=generate_recipe_image(recipe.Name,", ".join(ingredients_with_qty), steps=50)
            buffer = BytesIO()
            sd_image.save(buffer, format="JPEG")
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            image_data = f"data:image/jpeg;base64,{img_str}"

            ai_image_url = generate_food_image(
                recipe.Name,
                ", ".join(ingredients_with_qty),
                getattr(recipe, "RecipeInstructions_cleaned", recipe.Description)
            )
            # -----------------------
            # BUILD CONTEXT
            # -----------------------
            context_recipe = {
                "Name": recipe.Name,
                "Calories": recipe.Calories,
                "MealType": recipe.MealType,  # <--- NEW
                "RecipeInstructions": getattr(recipe, "RecipeInstructions_cleaned", recipe.Description),
                # ⭐ Show Pollinations image instead of CSV image
                "Images": image_data,
                "ingredients_with_qty": ingredients_with_qty,

                  # 🔥 NEW → Store in database in perfect format
                "ingredients": ",".join(ingredients_with_qty),
                # NEW → AI recipes have NO nutrients, so provide safe default
                "main_nutrients": {}
            }

            return render(request, "dashboard.html", {
                'profile': profile,
                "items": items,
                "form": form,
                "recipe": context_recipe,
                "favorites": favorites,
                "user_recipes": user_recipes, 
                "saved_dayplans": saved_dayplans, # <-- Add this
                "show_modal": True,
            })

        # ✅ Submit recipe to DB
        elif 'submit_recipe' in request.POST:
             # ---- RAW INGREDIENT INPUT (string like "['potato-2', 'onion-1']") ----
            raw_ing = request.POST.get("recipe_ingredients", "")

            # Clean brackets & quotes
            clean = raw_ing.strip("[]").replace("'", "").replace('"', "")

            # Split into list
            items = [i.strip() for i in clean.split(",") if i.strip()]

            # Convert into dict {"potato": 2, "onion": 1}
            ingredients_dict = {}

            for item in items:
                if "-" in item:
                    ing, qty = item.split("-", 1)
                    ing = ing.strip()

                    # Convert "1/4" or "2" into Python numeric
                    try:
                        if "/" in qty:
                            qty_value = eval(qty)
                        else:
                            qty_value = float(qty)
                    except:
                        qty_value = qty  # fallback to string

                    ingredients_dict[ing] = qty_value

            # ---- CALCULATE NUTRITION USING USDA API ----
            nutrition_totals = {}
            for ing, qty in ingredients_dict.items():
                try:
                    qty_in_grams = float(qty)  # ensure numeric for API scaling
                except:
                    qty_in_grams = 100  # fallback to 100g if unknown
                ing_nutrition = get_ingredient_nutrition(ing, qty_in_grams)
                for nut, data in ing_nutrition.items():
                    if nut not in nutrition_totals:
                        nutrition_totals[nut] = {"value": 0, "unit": data["unit"]}
                    nutrition_totals[nut]["value"] += data["value"] 
                    # ---- CONVERT TO "value unit" format ----
                # ---- FORMAT NUTRITION INTO "value unit" STRINGS ----
            formatted_nutrition = {}
            for nut, data in nutrition_totals.items():
                value = round(float(data["value"]), 2)
                unit = data["unit"]
                formatted_nutrition[nut] = f"{value} {unit}"      

             # ---- OPTIONAL: Extract main nutrients for popup (not saved in DB) ----
            main_nutrients_cleaned = extract_main_nutrients(nutrition_totals)
            # ---- SAVE RECIPE TO DATABASE ----
            recipe_obj = Recipe.objects.create(
                user=request.user,
                name=request.POST.get("recipe_name"),
                calories=request.POST.get("recipe_calories"),
                instructions=request.POST.get("recipe_instructions"),
                ingredients=ingredients_dict,
                nutrition_info=formatted_nutrition,   # ⭐ Store nutrition JSON
                main_nutrients=main_nutrients_cleaned,   
                meal_type=request.POST.get("meal_type", "Lunch"),   # ⭐ NEW
            )

            # 4️⃣ CONVERT BASE64 → IMAGE FILE AND SAVE
            image_b64 = request.POST.get("recipe_image_b64", "")
            if image_b64 and image_b64.startswith("data:image"):
                

                format, imgstr = image_b64.split(";base64,")
                ext = format.split("/")[-1]
                file_name = f"recipe_images/recipe_{recipe_obj.id}.{ext}"

                recipe_obj.image.save(
                    file_name,
                    ContentFile(base64.b64decode(imgstr)),
                    save=True
                )

            # ---- REDUCE PANTRY ITEMS QUANTITY ----
            for ing, used_qty in ingredients_dict.items():

                if not isinstance(used_qty, (int, float)):
                    try:
                        if "/" in str(used_qty):
                            used_qty = float(eval(used_qty))
                        else:
                            used_qty = float(used_qty)
                    except:
                        continue

                pantry_item = PantryItem.objects.filter(
                    user=request.user,
                    ingredient_name__iexact=ing
                ).first()

                if pantry_item:
                    pantry_item.qty -= used_qty

                    if pantry_item.qty <= 0:
                        pantry_item.delete()
                    else:
                        pantry_item.save()
            messages.success(request, "Recipe added successfully!")
            return redirect("dashboard") 
        
        elif request.method == "POST" and request.POST.get("action_type") == "save_day_plan":
            print("🔥 Save Day Plan POST entered")
            day_plan = request.session.get("day_plan")  # 3 recipes generated earlier

            
            if not day_plan:
                messages.error(request, "Generate a meal plan first.")
                return redirect("dashboard")

            saved_recipes = {}   # to store breakfast/lunch/dinner recipe objects

            for meal in day_plan:
                ingredients_list = meal.get("ingredients_with_qty", []) # already {item: qty}
                nutrition_totals = {}

                # Convert list to dict
                ingredients_dict = {}
                for item in ingredients_list:
                    try:
                        name, qty = item.rsplit("-", 1)
                        ingredients_dict[name.strip()] = float(qty)
                    except:
                        ingredients_dict[item] = 1  # fallback    

                # ---- CALCULATE NUTRITION USING USDA API ----
                for ing, qty in ingredients_dict.items():
                    try:
                        qty_in_grams = float(qty)
                    except:
                        qty_in_grams = 100
                    try:
                        ing_nutrition = get_ingredient_nutrition(ing, qty_in_grams)
                    except Exception as e:
                        print(f"⚠️ USDA API error for {ing}: {e}")
                        # fallback: empty nutrition so it doesn't break the save
                        ing_nutrition = {}
                    for nut, data in ing_nutrition.items():
                        if nut not in nutrition_totals:
                            nutrition_totals[nut] = {"value": 0, "unit": data["unit"]}
                        nutrition_totals[nut]["value"] += data["value"]

                # ---- FORMAT "value unit" ----
                formatted_nutrition = {
                    nut: f"{round(float(data['value']), 2)} {data['unit']}"
                    for nut, data in nutrition_totals.items()
                }

                # ---- MAIN NUTRIENTS ----
                main_nutrients_cleaned = extract_main_nutrients(nutrition_totals)

                # Save image from base64 to media
                image_b64 = meal["image"]
                if image_b64.startswith("data:image"):
                    format, imgstr = image_b64.split(";base64,")
                    ext = format.split("/")[-1]


                    # ---- SAVE RECIPE ----
                    recipe_obj = Recipe.objects.create(
                        user=request.user,
                        name=meal.get("Name") or meal.get("meal"),
                        ingredients=ingredients_dict,
                        instructions=meal.get("instructions") or meal.get("RecipeInstructions_cleaned"),
                        meal_type=meal.get("MealType") or meal.get("meal_type"),        # already provided in DF
                        nutrition_info=formatted_nutrition,
                        main_nutrients=main_nutrients_cleaned,
                    )

                    ## Save image using recipe ID
                    file_name = f"recipe_images/recipe_{recipe_obj.id}.{ext}"
                    content_file = ContentFile(base64.b64decode(imgstr))
                    recipe_obj.image.save(file_name, content_file, save=True)
        
                # store based on meal type
                saved_recipes[recipe_obj.meal_type]  = recipe_obj

            # ---- SAVE TO DAYPLAN ----
            DayPlan.objects.create(
                user=request.user,
                breakfast=saved_recipes.get("Breakfast"),
                lunch=saved_recipes.get("Lunch"),
                dinner=saved_recipes.get("Dinner"),
            )

            messages.success(request, "Day plan and recipes saved successfully!")
            return redirect("dashboard")



        elif request.POST.get("action_type") == "generate_day_meal":
            print("🔥 Generate Day Meal clicked")
            request.session["show_day_plan"] = True  

            ingredient_ids = request.POST.get("selectedIngredientsday", "")
            ids = [int(i) for i in ingredient_ids.split(",") if i.isdigit()]
            print("Selected ingredient IDs:", ids)  # ✅ Debug: show ingredients in terminal
            if not ids:
                messages.error(request, "Please select ingredients.")
                return redirect("dashboard")

            pantry_items = PantryItem.objects.filter(id__in=ids)
            serving_size = int(request.POST.get("serving_size", 2))
            
            saved_recipe_names = set(
                Recipe.objects.filter(user=request.user)
                .values_list("name", flat=True)
            )

            # Call meal-plan generator with 1 day of 3 meals
            day_df = generate_meal_plan(
                user=request.user,
                pantry_items=pantry_items,
                days=1,
                meals_per_day=3,
                exclude_names=saved_recipe_names,     # <--- ✨ NEW
                serving_size=serving_size
                
            )

            day_plan_records = []
            for _, row in day_df.iterrows():
                ingredients_with_qty = combine_ing_qty(
                    row.get("RecipeIngredientParts_cleaned", ""),
                    row.get("RecipeIngredientQuantities_cleaned", "")
                )
            
                # Generate image
                sd_image = generate_recipe_image(
                    row["Name"],
                    ", ".join(ingredients_with_qty),
                    steps=50
                )
                # Convert image to base64 for display in modal
                buffer = BytesIO()
                sd_image.save(buffer, format="JPEG")
                buffer.seek(0)
                img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                image_data = f"data:image/jpeg;base64,{img_str}"

                # Generate image
                ai_image = generate_food_image(
                    row["Name"],
                    ", ".join(ingredients_with_qty),
                    row.get("RecipeInstructions_cleaned", row.get("Description", ""))
                )

                meal_dict = {
                    "Name": row.get("Name", ""),
                    "MealType": row.get("MealType", ""),
                    "day_of_week": row.get("day_of_week", ""),  # optional
                    "RecipeInstructions_cleaned": row.get("RecipeInstructions_cleaned", row.get("Description", "")),
                    "ingredients_with_qty": ingredients_with_qty,  # ✅ Python list
                    "image": image_data
                }

                day_plan_records.append(meal_dict)

        
            # Now day_plan_records is a list of plain dicts
            request.session["day_plan"] = day_plan_records

            print("✅ Full Day Meal Plan Generated")
            for meal in day_plan_records:
                print(f"{meal['MealType']}: {meal['Name']}")
           
            return render(request, "dashboard.html", {
                "profile": profile,
                "items": items,
                "form": form,
                "day_plan_meals": day_plan_records,
                "show_day_plan_modal": True,
                "user_recipes": user_recipes, 
                "selected_ingredient_ids": ingredient_ids,
                "serving_size": serving_size
            })
        
        # --- Regenerate single meal in session ---
        elif request.POST.get("action_type") == "generate_day_meal_single":
            meal_type_to_regen = request.POST.get("meal_type_to_regen")
            ingredient_ids = request.POST.get("selectedIngredientsday", "")
            ids = [int(i) for i in ingredient_ids.split(",") if i.isdigit()]
            serving_size = int(request.POST.get("serving_size", 2))

            if not ids:
                messages.error(request, "Please select ingredients.")
                return redirect("dashboard")

            pantry_items = PantryItem.objects.filter(id__in=ids)

            # Exclude already existing recipes except for the one we want to regenerate
            saved_recipe_names = set(
                Recipe.objects.filter(user=request.user)
                .values_list("name", flat=True)
            )
            current_day_plan = request.session.get("day_plan", [])

            # Generate only 1 meal of the specific type
            new_meal_df = generate_meal_plan(
                user=request.user,
                pantry_items=pantry_items,
                days=1,
                meals_per_day=1,
                exclude_names=saved_recipe_names,
                serving_size=serving_size
            )

            if not new_meal_df.empty:
                row = new_meal_df.iloc[0]
                ingredients_with_qty = combine_ing_qty(
                    row.get("RecipeIngredientParts_cleaned", ""),
                    row.get("RecipeIngredientQuantities_cleaned", "")
                )
                # Generate image
                sd_image = generate_recipe_image(
                    row["Name"],
                    ", ".join(ingredients_with_qty),
                    steps=50
                )
                # Convert image to base64 for display in modal
                buffer = BytesIO()
                sd_image.save(buffer, format="JPEG")
                buffer.seek(0)
                img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                image_data = f"data:image/jpeg;base64,{img_str}"

                ai_image = generate_food_image(
                    row["Name"],
                    ", ".join(ingredients_with_qty),
                    row.get("RecipeInstructions_cleaned", row.get("Description", ""))
                )

                regenerated_meal = {
                    "Name": row.get("Name", ""),
                    "MealType": row.get("MealType", ""),
                    "day_of_week": row.get("day_of_week", ""),
                    "RecipeInstructions_cleaned": row.get("RecipeInstructions_cleaned", row.get("Description", "")),
                    "ingredients_with_qty": ingredients_with_qty,
                    "image": image_data
                }

                # Replace the meal in session with regenerated one
                for i, meal in enumerate(current_day_plan):
                    if meal["MealType"] == meal_type_to_regen:
                        current_day_plan[i] = regenerated_meal
                        break

                request.session["day_plan"] = current_day_plan
                print(f"🔄 Regenerated {meal_type_to_regen}: {regenerated_meal['Name']}")

            return render(request, "dashboard.html", {
                "profile": profile,
                "items": items,
                "form": form,
                "user_recipes": user_recipes,
                "favorites": favorites,
                "day_plan_meals": request.session.get("day_plan", []),
                "show_day_plan_modal": request.session.get("show_day_plan", False),
                "user_recipes": user_recipes,
                "selected_ingredient_ids": ingredient_ids,
                "serving_size": serving_size
            })

       
    # ✅ This handles GET request (page load)
    return render(request, "dashboard.html", {
        'profile': profile,
        'form': form,
        "items": PantryItem.objects.filter(user=request.user),  
        'today': today,
        "recipe": context_recipe,  # must include this
        "favorites": favorites, 
        "user_recipes": user_recipes,  
        "saved_dayplans": saved_dayplans, # <-- Add this
        "day_favorites": day_favorites,
        "show_modal": True,
    })

def clear_day_plan(request):
    """
    Clears the generated day plan stored in the session
    when the user presses the Close button.
    """
    if 'day_plan' in request.session:
        del request.session['day_plan']

    request.session['show_day_plan'] = False
    return redirect('dashboard')

@login_required
def edit_pantry_item(request, item_id):
    item = get_object_or_404(PantryItem,id=item_id, user=request.user)
    if request.method == "POST":
        form = PantryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Pantry item updated successfully!")
        else:
            messages.error(request, "Error updating item.")
    return redirect("dashboard")


@login_required
def delete_pantry_item(request, item_id):
    try:
        item = get_object_or_404(PantryItem,id=item_id, user=request.user)
        item.delete()
        messages.success(request, "Pantry item deleted successfully!")
    except PantryItem.DoesNotExist:
        messages.error(request, "Item not found.")
    return redirect("dashboard")

@csrf_exempt
@login_required
def toggle_favorite(request):
    if request.method == "POST":
        recipe_name = request.POST.get("recipe_name")
        if not recipe_name:
            return JsonResponse({"status": "error", "message": "No recipe name provided"})

        # Try to find the recipe
        recipe = Recipe.objects.filter(user=request.user, name=recipe_name).first()

        # If recipe does NOT exist, auto-create from session AI recipe
        if not recipe:
            ai_recipe = request.session.get("last_ai_recipe")
            if not ai_recipe:
                return JsonResponse({"status": "error", "message": "Recipe data missing"})

            recipe = Recipe.objects.create(
                user=request.user,
                name=ai_recipe["Name"],
                calories=ai_recipe["Calories"],
                instructions=ai_recipe["RecipeInstructions"],
                image=ai_recipe["Images"],
                ingredients=ai_recipe["ingredients_dict"],  # JSON dict
                meal_type=ai_recipe.get("MealType", "Lunch"),  # ⭐ NEW
            )

        # Toggle favorite
        favorite, created = FavoriteRecipe.objects.get_or_create(user=request.user, recipe=recipe)

        if not created:
            favorite.delete()
            recipe.is_favorite = False
            recipe.save()
            return JsonResponse({"status": "removed from favorites"})
        else:
            recipe.is_favorite = True
            recipe.save()
            return JsonResponse({"status": "added to favorites"})

    return JsonResponse({"status": "invalid request"}, status=400)


@login_required
def get_favorites(request):
    favorites = FavoriteRecipe.objects.filter(user=request.user).select_related("recipe")

    data = []
    for fav in favorites:
        recipe = fav.recipe
        data.append({
                    "name": recipe.name,
                    "image": recipe.image.url if recipe.image else "",
                    "calories": recipe.calories,
                    "ingredients": recipe.ingredients if isinstance(recipe.ingredients, dict) else {},
                    "instructions": recipe.instructions or "",
                    "main_nutritents": recipe.main_nutrients if isinstance(recipe.main_nutrients, dict) else {},
                })
            
        
    return JsonResponse({"favorites": data})


@login_required
def delete_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)
    recipe.delete()
    messages.success(request, "Recipe deleted successfully!")
    return redirect('dashboard')


@login_required
def add_dayplan_favorite(request, plan_id):
    plan = get_object_or_404(DayPlan, id=plan_id, user=request.user)
    plan.is_favorite = True
    plan.save()
    messages.success(request, "Day plan added to favorites ❤️")
    return redirect("dashboard")

@login_required
def remove_dayplan_favorite(request, plan_id):
    plan = get_object_or_404(DayPlan, id=plan_id, user=request.user)
    plan.is_favorite = False
    plan.save()
    messages.success(request, "Day plan removed from favorites 💔")
    return redirect("dashboard")

@login_required
def delete_dayplan(request, plan_id):
    plan = get_object_or_404(DayPlan, id=plan_id, user=request.user)
    plan.delete()
    messages.success(request, "Day plan deleted successfully! 🗑️")
    return redirect('dashboard')