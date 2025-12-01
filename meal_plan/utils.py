from diffusers import StableDiffusionPipeline
import torch
from PIL import Image

# Load model once (can be reused)
pipe = None
def get_pipe():
    global pipe
    if pipe is None:
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
        )
        pipe = pipe.to("cuda")  # or "cpu" if no GPU
    return pipe

def generate_recipe_image(recipe_name, ingredients, steps=50):
    prompt = f"A high-quality, appetizing photo of {recipe_name} with {' ,'.join(ingredients)}, top-down food photography"
    pipe = get_pipe()
    image = pipe(prompt, guidance_scale=7.5, num_inference_steps=steps).images[0]
    return image



def convert_to_grams(quantity, unit, ingredient_name=None):
    """
    Convert quantity with unit to grams for USDA API.
    quantity: float
    unit: str ('g', 'kg', 'ml', 'l', 'cup', etc.)
    ingredient_name: optional, for density-based conversion
    """
    unit = unit.lower()
    if unit in ["g", "gram", "grams", "Gram"]:
        return quantity
    elif unit in ["kg", "kilogram", "kilograms", "Kilogram"]:
        return quantity * 1000
    elif unit in ["ml", "milliliter", "milliliters", "Millilitre"]:
        # Use density if known
        density = get_density(ingredient_name)  # in g/ml
        return quantity * (density if density else 1)
    elif unit in ["l", "liter", "liters","L", "Litre"]:
        density = get_density(ingredient_name)  # in g/ml
        return quantity * 1000 * (density if density else 1)
    else:
        # fallback: assume quantity in grams
        return quantity

def get_density(ingredient_name):
    """
    Simple lookup table for some common liquids.
    Could be expanded to more ingredients or external API.
    """
    densities = {
        "milk": 1.03,        # 1 liter = 1030g
        "water": 1.0,
        "olive oil": 0.92,
        "honey": 1.42,
        "yogurt": 1.03,
    }
    return densities.get(ingredient_name.lower(), 1)
