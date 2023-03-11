from django.contrib import admin
from django.urls import path
from drinks import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('createUser/', views.create_user, name=""),
    path('updateUserInfo/', views.update_user_data),
    path('sendAndGetMyName/<str:name>/', views.send_name,),
    path('whiskApp/webExtension/getRecipeInformation/', views.get_recipe_information_web_extension, name="website_url"),
    path('createRecipeCategory/', views.create_recipe_category),
    path('getAllCategories/', views.get_all_categories),
    path('whiskApp/webExtension/saveRecipeInfo/', views.save_recipe_two),
    path('getAllRecipes/', views.get_all_recipes),
    path('getRecipeData/', views.get_recipe_data)
]
