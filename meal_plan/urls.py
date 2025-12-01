from django.urls import path
from. import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('dashboard.html', views.dashboard, name='dashboard'),
    path("pantry/add/", views.dashboard, name="add_pantry_item"),   # Form posts to dashboard
    path('pantry/edit/<int:item_id>/', views.edit_pantry_item, name='edit_pantry_item'),
    path('pantry/delete/<int:item_id>/', views.delete_pantry_item, name='delete_pantry_item'),
    # ⭐ Add these lines for Favorites API
    path('get-favorites/', views.get_favorites, name='get_favorites'),
    path('toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('delete_recipe/<int:recipe_id>/', views.delete_recipe, name='delete_recipe'),
    path('clear-day-plan/', views.clear_day_plan, name='clear_day_plan'),
    path("dayplan/<int:plan_id>/favorite/", views.add_dayplan_favorite, name="add_dayplan_favorite"),
    path("dayplan/<int:plan_id>/unfavorite/", views.remove_dayplan_favorite, name="remove_dayplan_favorite"),
    path('delete_dayplan/<int:plan_id>/', views.delete_dayplan, name='delete_dayplan'),

]