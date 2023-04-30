from django.contrib import admin
from django.urls import path
from drinks import views

urlpatterns = [
    path('', views.home, name='home'),
    path('manager-markets/', views.manager_markets, name='manager_markets'),
    path('login-manager-market/', views.login_manager_market, name='login_manager_market'),
    path('manager_markets_home_page/', views.manager_markets_home_page, name='manager_markets_home_page'),
    path('change_location_page/', views.change_location_page, name='change_location_page'),
    path('change_market_location/', views.change_market_location, name="change_market_location"),
    path('get_market_data/', views.get_market_data, name='get_market_data'),
    path('getItemsFromExcel/', views.get_item_from_excel),
    # user Apis
    path('createUser/', views.create_user, name=""),
    path('updateUserInfo/', views.update_user_data),
    path('getUserData/', views.get_user_data),
    # webExtension Apis
    path('whiskApp/webExtension/getRecipeInformation/', views.get_recipe_information_web_extension, name="website_url"),
    path('whiskApp/webExtension/saveRecipeInfo/', views.save_recipe),
    # recipe category Apis
    path('createRecipeCategory/', views.create_recipe_category),
    path('getAllCategories/', views.get_all_recipe_categories),
    path('renameRecipeCategory/', views.rename_recipe_category),
    path('deleteRecipeCategory/', views.delete_recipe_category),
    # recipe Apis
    path('getAllRecipes/', views.get_all_recipes),
    path('getRecipeIngredients/', views.get_recipe_ingredients),
    path('getRecipeSteps/', views.get_recipe_steps),
    path('deleteRecipe/', views.delete_recipe),
    # Shopping List Category
    path('createShoppingListCategory/', views.create_shopping_list_category),
    path('deleteShoppingListCategory/', views.delete_shopping_list_category),
    path('renameShoppingListCategory/', views.rename_shopping_list_category),
    path('getAllShoppingListCategory/', views.get_all_shopping_list_categories),
    path('getShoppingListItems/', views.get_shopping_list_items),
    path('checkAvailability/', views.check_availability),
    # Shopping List Item
    path('addNewItemToShoppingList/', views.add_new_shopping_list_item),
    path('toggleItemsStatus/', views.toggle_items_status),
    path('deleteShoppingListItem/', views.delete_shopping_list_item),
    # Home Screen
    path('selectShoppingListInHomeScreen/', views.select_shopping_list_in_home_screen),
    path('getHomeScreenData/', views.get_home_screen_data),
    path('getAllEditorsChoice/', views.get_all_editors_choice_recipes),
    # Django Admin must change it to more secure
    path('admin/', admin.site.urls),
    # test Api
    path('sendAndGetMyName/<str:name>/', views.send_name, ),
    # ocr
    path('generateRecipeUsingGPT/', views.generate_recipe_ocr),
]

handler404 = 'drinks.views.error_404_view'
