# 🥗 AI Powered Nutritional Recipe Planner
A Smart Solution for Personalized & Healthy Meal Planning

The AI Powered Nutritional Recipe Planner is a web-based application that generates personalized and nutritionally accurate meal plans based on user preferences, dietary restrictions, health goals, and available pantry ingredients. The system helps users plan healthy meals efficiently using intelligent recipe generation, USDA-backed nutritional data, and AI-generated food images.

# Features
# Personalized Meal Planning

Users can set:
-Dietary preferences (vegan, vegetarian, gluten-free, etc.)
-Allergies and ingredient restrictions
-Health goals (weight loss, maintenance, muscle gain)

# USDA Nutritional Data Integration
-Each recipe includes:
    Calories
    Proteins
    Carbohydrates
    Fats
    Vitamins & minerals
Powered by USDA Food Central API.

# AI Generated Recipe Images

Uses Stable Diffusion to generate:

  High-quality food visuals
  Images based on ingredients & recipe descriptions

# Pantry Tracker

Users manage ingredients they have
System suggests meals based on pantry items
Helps reduce food waste

# Recipe Generator

Step-by-step cooking instructions
Adaptable serving sizes
Nutritional breakdown
Multi-language support

# User Profile Management

Edit dietary preferences
Track meal history
Save favorite recipes

# 🏗️ System Architecture
Frontend

  Built with:
    HTML5, CSS3
    JavaScript 
    Responsive design with dynamic UI updates

  Provides pages for:
    Profile management
    Pantry tracker
    Meal/recipe generation
    AI image display

Backend (Django Framework)

  Handles:
    User authentication
    Meal generation based on dietary data
    USDA API communication
    Nutritional calculations
    Pantry item processing
    Stable Diffusion image generation

AI/ML Components
  Stable Diffusion → Generates recipe images

Recipe Generation Model
  Creates personalized recipes and steps

Nutritional Estimator
  Computes calories, macros, and nutrients

Database (PostgreSQL)

  Stores:
    Users & dietary profiles
    Pantry items
    Generated recipes
    Nutritional data
    Meal plans
    AI-generated images
Ensures secure, fast, and scalable data management.

Media Handling
  Django Media Storage for uploads & generated images
  Pillow for image optimization

 # 📁 Tech Stack
Layer	Technologies
Frontend	HTML, CSS, JavaScript
Backend	Python, Django
Database	PostgreSQL
AI/ML	Stable Diffusion, Custom Recipe Model
Image Processing Pillow
External API	USDA Food Central API
 #  Project Goals

Promote healthy eating habits
Simplify meal planning
Provide nutritionally accurate recipes
Reduce food waste through pantry tracking
Make personalized diet management accessible and smart


# 📜 License

This project is licensed under the MIT License.
