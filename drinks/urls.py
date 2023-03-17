from django.contrib import admin
from django.urls import path
from drinks import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    # test Api
    path('sendAndGetMyName/<str:name>/', views.send_name,),
    # user Apis
    path('createUser/', views.create_user, name=""),
    path('updateUserInfo/', views.update_user_data),
    # webExtension Apis
    path('whiskApp/webExtension/getRecipeInformation/', views.get_recipe_information_web_extension, name="website_url"),
    path('whiskApp/webExtension/saveRecipeInfo/', views.save_recipe_two),
    # recipe category Apis
    path('createRecipeCategory/', views.create_recipe_category),
    path('getAllCategories/', views.get_all_recipe_categories),
    path('renameRecipeCategory/', views.rename_recipe_category),
    path('deleteRecipeCategory/', views.delete_recipe_category),
    # recipe Apis
    path('getAllRecipes/', views.get_all_recipes),
    path('getRecipeData/', views.get_recipe_data),
    path('deleteRecipe/', views.delete_recipe),
    # Shopping List Category
    path('createShoppingListCategory/', views.create_shopping_list_category),
    path('deleteShoppingListCategory/', views.delete_shopping_list_category),
    path('renameShoppingListCategory/', views.rename_shopping_list_category),
    path('getAllShoppingListCategory/', views.get_all_shopping_list_categories),
    # Shopping List Item
    path('addNewItemToShoppingList/', views.add_new_shopping_list_item)
]
