from django.db import models
from django.contrib.auth.models import User
#from django.contrib.postgres.fields import JSONField  # If using PostgreSQL
from django.utils import timezone


class Profile(models.Model):
    # One-to-One relationship with Django's built-in User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Additional profile information
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other'),
        ],
        blank=True
    )
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    goal = models.CharField(
        max_length=20,
        choices=[
            ('Weight Loss', 'Weight Loss'),
            ('Weight Gain', 'Weight Gain'),
            ('Maintenance', 'Maintenance'),
        ],
        blank=True
    )
    dietary_pref = models.CharField(
        max_length=30,
        choices=[
            ('Vegan', 'Vegan'),
            ('Vegetarian', 'Vegetarian'),
            ('Keto', 'Keto'),
            ('Paleo', 'Paleo'),
            ('Gluten-Free', 'Gluten-Free'),
            ('Dairy-Free', 'Dairy-Free'),
            ('Pescatarian', 'Pescatarian'),
            ('Low-Carb', 'Low-Carb'),
            ('Low-Fat', 'Low-Fat'),
            ('Nut-Free', 'Nut-Free'),
            ('Soy-Free', 'Soy-Free'),
            ('Halal', 'Halal'),
            ('Kosher', 'Kosher'),
            ('None', 'None'),
        ],
        blank=True
    )
    allergy_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def username(self):
        return self.user.username

    @property
    def email(self):
        return self.user.email


class PantryItem(models.Model):
    CATEGORY_CHOICES = [
        ('Veggies', 'Veggies'),
        ('Dairy', 'Dairy'),
        ('Meat', 'Meat'),
        ('Spices', 'Spices'),
        ('Others', 'Others'),
    ]
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('L', 'Litre'),
        ('ml', 'Millilitre'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pantry_items')  # 🔗 link to user
    ingredient_name = models.CharField(max_length=255)
    qty = models.FloatField()
    unit = models.CharField(max_length=30, choices=UNIT_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    expire_date = models.DateField(null=True, blank=True)
    nutrition_info = models.JSONField(default=dict, null=True, blank=True) 
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"{self.ingredient_name} ({self.qty} {self.unit})"


    
class Recipe(models.Model):
    MEAL_TYPE_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snack', 'Snack'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipes")
    name = models.CharField(max_length=255)
    calories = models.FloatField(null=True, blank=True)
    instructions = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='recipe_images/', blank=True, null=True)
    # JSON dict format {"potato": 2, "onion": 1}
    ingredients = models.JSONField(default=dict ,blank=True)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES, default="Lunch")  # ⭐ NEW
    nutrition_info = models.JSONField(blank=True, null=True)  # Recipe-level nutrition JSON
    # ⭐ NEW FIELD — your formatted nutrients {'unit': 'G', 'value': 0.0}
    main_nutrients = models.JSONField(blank=True, null=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        fav = "⭐" if self.is_favorite else ""
        return f"{fav}{self.name} ({self.user.username})"


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.user.username} ❤️ {self.recipe.name}"
    


class DayPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    breakfast = models.ForeignKey(
        "Recipe", on_delete=models.CASCADE, related_name="breakfast_plans"
    )
    lunch = models.ForeignKey(
        "Recipe", on_delete=models.CASCADE, related_name="lunch_plans"
    )
    dinner = models.ForeignKey(
        "Recipe", on_delete=models.CASCADE, related_name="dinner_plans"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)  # ⭐ NEW FIELD

    def __str__(self):
        return f"{self.user.username} – {self.date} ({self.date.strftime('%A')})"
