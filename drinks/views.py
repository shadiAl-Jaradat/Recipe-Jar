import unicodedata
from datetime import datetime
import googlemaps
from django.db.models import Window
from django.db.models import F
from django.db.models.functions import RowNumber
from googleapiclient.errors import HttpError
from rest_framework.generics import get_object_or_404
from .serializer import IngredientSerializer, RecipeCategorySerializer, StepSerializer, \
    UserSerializer, ShoppingListCategorySerializer, RecipeSerializer
from .models import User, Recipe, Ingredient, Step, RecipeCategory, Unit, Item, ShoppingListCategory, ShoppingListItem, \
    Market, MarketItem
from googleapiclient.discovery import build
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from django.http import JsonResponse, HttpResponseBadRequest
from recipe_scrapers import scrape_me
from uuid import UUID, uuid4
from quantulum3 import parser
from ingredient_parser.en import parse
from django.shortcuts import render
import pandas as pd
import requests
import re
from .secrets import openai


def error_404_view(request, exception):
    return render(request, 'whiskTemplates/404.html', status=404)


def home(request):
    context = {'title': 'Whisk App'}
    return render(request, 'whiskTemplates/home.html', context)


def manager_markets(request):
    context = {'title': 'Whisk App managers'}
    return render(request, 'whiskTemplates/managerMarkets.html', context)


def manager_markets_home_page(request):
    market_id = request.GET.get('market_id')
    return render(request, 'whiskTemplates/managerMarketsHomePage.html', {'market_id': market_id})


def change_location_page(request):
    market_id = request.GET.get('market_id')
    return render(request, 'whiskTemplates/changeLocation.html', {'market_id': market_id})


def login_manager_market(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        manager_username = data['email']
        manager_password = data['password']

        market = Market.objects.filter(managerUserName=manager_username, managerPassword=manager_password).first()
        if market:
            # If a match is found, return success: True and the market ID
            return JsonResponse({'success': True, 'message': 'Login successful', 'market_id': str(market.id)})
        else:
            # If no match is found, return success: False
            return JsonResponse({'success': False, 'message': 'User not found or password incorrect'}, )
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


def get_market_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        market_id = data['marketID']
        market = Market.objects.filter(id=market_id).first()
        market_data = {
            "name": market.name,
            "location": market.location,
            "logo": market.logo
        }
        return JsonResponse(market_data, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


def change_market_location(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        market_id = data['id']
        new_location = data['newLocation']
        market = Market.objects.filter(id=market_id).first()
        market.location = new_location
        market.save()
        market_data = {
            "name": market.name,
            "location": new_location,
        }
        return JsonResponse(market_data, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_item_from_excel(request):
    if request.method == 'POST':
        # Get the uploaded file from the request
        file = request.FILES['file']
        market_id = request.data.get('marketID')
        market = Market.objects.filter(id=market_id).first()
        # Load the Excel file using pandas
        df = pd.read_excel(file)
        # Get the values in the "Item Name" column
        item_names = df['Item name'].tolist()

        for item_name in item_names:
            try:
                item_from_db = Item.objects.get(name=item_name)
                item = item_from_db
            except Item.DoesNotExist:
                items_length = Item.objects.count()
                item = Item(id=items_length + 1, name=item_name)
                item.save()

            market_item_id = uuid4()
            # Create the marketItem instance
            market_item = MarketItem(
                id=market_item_id,
                itemID=item,
                marketID=market
            )
            market_item.save()

        # Return the list of item names as a JSON response
        return JsonResponse({'item_names': item_names})
    # If the request method is not POST, return an error response
    return JsonResponse({'error': 'Invalid request method'})


# User Functionality APIs ################################

@api_view(['POST'])
def create_user(request):
    if request.method == 'POST':
        # load the request body data as a JSON object.
        data = json.loads(request.body)
        # create a new User object using the data from the request.
        user = User(
            id=data['userID'],
            firstName=data['firstName'],
            lastName=data['lastName'],
            phoneNumber=data['phoneNumber'],
            age=data['age'],
            weight=data['weight'],
            height=data['height'],
        )
        # save the new User object to the database.
        user.save()
        # serialize the User object and return it as a JSON response.
        serialized_user = UserSerializer(user)
        return JsonResponse(serialized_user.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def get_user_data(request):
    if request.method == 'POST':
        # Get the user ID from the request data.
        user_id = request.data.get('userID')
        # Check if the user ID is present in the request data.
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Try to fetch the user data from the database using the user ID.
        try:
            user = User.objects.get(pk=user_id)
        except:
            # If user is not found in database then return a 404 response.
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the User object and return it as a JSON response.
        serialized_user = UserSerializer(user)
        return JsonResponse(serialized_user.data, status=status.HTTP_200_OK)
    else:
        # Return a bad request response if the request method is not POST.
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def update_user_data(request):
    if request.method == 'POST':
        # Get the user ID from the request data
        user_id = request.data.get('id')
        # Try to fetch the user data from the database using the user ID.
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # If user is not found in database then return a 404 response.
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Update the User object using the request data and serialize it.
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            # If the request data is invalid, return a 400 Bad Request response with the validation errors.
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Return a bad request response if the request method is not POST.
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


# Recipe Category APIs ################################

@api_view(['POST'])
def create_recipe_category(request):
    if request.method == 'POST':
        # Parse request data
        data = json.loads(request.body)
        # generate unique ID for the new category.
        category_uuid = uuid4()

        # Get category name, user ID, and order ID.
        name = data['name']
        user_id = data['userID']
        temp_user = User.objects.get(pk=user_id)
        categories = RecipeCategory.objects.filter(user=temp_user).order_by('orderID')
        order_id = len(categories) + 1

        # Create new RecipeCategory object and save it to the database.
        temp_category = RecipeCategory(
            id=category_uuid,
            name=name,
            orderID=order_id,
            user=temp_user
        )
        temp_category.save()

        # Serialize the new RecipeCategory object and return it as a JSON response with a 200 status code.
        serialized_category = RecipeCategorySerializer(temp_category)

        return JsonResponse(serialized_category.data, status=status.HTTP_200_OK)
    else:
        # Return a bad request response if the request method is not POST.
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def rename_recipe_category(request):
    if request.method == 'POST':
        # Retrieve the category_id and new_name from the request data
        category_id = request.data.get('id')
        new_name = request.data.get('newName')

        # Try to get the RecipeCategory object with the specified category_id
        # If it doesn't exist, return 404 status with an error message
        category = get_object_or_404(RecipeCategory, id=category_id)

        # Update the category name with the new name
        category.name = new_name

        # Save the changes to the category object
        category.save()

        # Serialize the updated category object
        serializer = RecipeCategorySerializer(category)

        # Return a JSON response with the serialized category data and a status of 200 OK
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        # Return a JSON response with an error message and a status of 400 BAD REQUEST if request method is not POST
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def delete_recipe_category(request):
    if request.method == 'POST':
        # Extract the category id from the request body using the get() method
        category_id = request.data.get('id')

        # Use get_object_or_404 to get the category object with the given id or
        # return a 404 response if it does not exist
        category = get_object_or_404(RecipeCategory, id=category_id)

        # Call the delete method on the category object to remove it from the database
        category.delete()

        # Return a 204 status code to indicate that the category has been successfully deleted,
        # along with a message indicating that the category has been deleted
        return Response({'message': ' Recipe Category deleted :( '}, status=status.HTTP_204_NO_CONTENT)
    else:
        # If the request method is not POST, return a 400 status code with an error message
        # indicating that the API only accepts POST requests
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_all_recipe_categories(request):
    if request.method == 'POST':
        # retrieve the user ID from the request data
        user_id = request.data.get('userID')

        # check if the user ID is present in the request data
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Get the user object from the database based on the user ID
            user = User.objects.get(pk=user_id)
        except:
            # If the user does not exist, return a 404 Not Found response
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # retrieve all the recipe categories for the user and annotate them with a new column "orderIDNEW"
        categories = RecipeCategory.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
                order_by=F('orderID').asc()
            )
        ).filter(user=user_id).order_by('orderID')

        # exclude any categories with a null orderID value and retrieve only the id, name, and orderIDNEW fields
        categories = categories.exclude(orderID__isnull=True).values('id', 'name', 'orderIDNEW')

        # create a list to store the data for each category and its associated recipes
        list_data = []

        for category in categories:
            # retrieve all the recipes associated with the category
            recipes_of_this_category = Recipe.objects.filter(category=category['id'])

            # append the category data along with the number of recipes associated with it to the list
            list_data.append(
                {
                    'id': category['id'],
                    'name': category['name'],
                    'orderID': category['orderIDNEW'],
                    'numOfRecipes': len(recipes_of_this_category)
                }
            )

        # return the list of category data with a 200 OK response status
        return Response(list_data, status=status.HTTP_200_OK)
    else:
        # Return a 400 Bad Request response if the request method is not POST
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


# Recipe APIs ################################

@api_view(['POST'])
def delete_recipe(request):
    if request.method == 'POST':
        # extract the recipe id from the request data
        recipe_id = request.data.get('id')

        # fetch the recipe object from the database, or raise a 404 error if it doesn't exist
        recipe = get_object_or_404(Recipe, id=recipe_id)

        # delete the recipe object from the database
        recipe.delete()

        # return a success message with a 204 status code
        return Response({'message': ' Recipe deleted :( '}, status=status.HTTP_204_NO_CONTENT)
    else:
        # return an error message if the request method is not POST
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_all_recipes(request):
    if request.method == 'POST':
        # loads the request body as JSON and extracts the categoryID field.
        data = json.loads(request.body)
        category_id = UUID(data['categoryID'])

        # checks if categoryID is present in the request, and if not, returns a bad request error response.
        if not category_id:
            return Response({"error": "categoryID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # retrieve the RecipeCategory object with the specified ID,
        # and returns a not found error response if it doesn't exist.
        try:
            category = RecipeCategory.objects.get(pk=category_id)
        except RecipeCategory.DoesNotExist:
            return Response({"error": f"User with ID {category_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # retrieves all Recipe objects associated with the specified category,
        # and annotates them with a new orderIDNEW field using the Window and RowNumber functions
        # from Django's Window expressions. It also excludes any recipes that have a null orderID. If an error occurs,
        # it returns a JSON response with a description of the error.
        try:
            recipes = Recipe.objects.annotate(
                orderIDNEW=Window(
                    expression=RowNumber(),
                    order_by=F('orderID').asc()
                )
            ).filter(category=category).order_by('orderID').exclude(orderID__isnull=True).values('id', 'videoUrl',
                                                                                                 'videoTitle',
                                                                                                 'videoImage',
                                                                                                 'videoDuration',
                                                                                                 'videoChannelName',
                                                                                                 'title', 'time',
                                                                                                 'pictureUrl',
                                                                                                 'isEditorChoice',
                                                                                                 'orderIDNEW')
        except Exception as e:
            return JsonResponse({'error': f'Error occurred while processing text: {e}.'}, status=405)

        # creates a list of new recipe objects that have the videoData and recipeData
        # extracted from the original query results.
        new_list_of_recipes = []

        for recipe in recipes:
            video_data = {
                'youtubeLink': recipe['videoUrl'],
                'title': recipe['videoTitle'],
                'image': recipe['videoImage'],
                'duration': recipe['videoDuration'],
                'channelName': recipe['videoChannelName']
            }
            recipe_data = {
                'id': recipe['id'],
                'name': recipe['title'],
                'time': recipe['time'],
                'pictureUrl': recipe['pictureUrl'],
                'videoUrl': video_data,
                'isEditorChoice': recipe['isEditorChoice'],
                'orderID': recipe['orderIDNEW']
            }
            new_list_of_recipes.append(recipe_data)

        # returns the new list of recipes as a JSON response with a status of 200 OK
        return Response(new_list_of_recipes, status=status.HTTP_200_OK)
    else:
        # return an error message if the request method is not POST
        return JsonResponse({'error': 'this API is POST API'}, status=405)


@api_view(['POST'])
def get_recipe_ingredients(request):
    if request.method == 'POST':
        # load data from the request body
        data = json.loads(request.body)

        # retrieve the recipe ID from the data
        recipe_id = UUID(data['RecipeID'])

        # get the recipe object with the given ID
        recipe = Recipe.objects.get(pk=recipe_id)

        # retrieve all the ingredients for the recipe
        ingredients = Ingredient.objects.filter(recipe=recipe)

        # serialize the ingredients using the IngredientSerializer
        serialized_ingredients = IngredientSerializer(ingredients, many=True)

        # create a list of ingredients with additional data
        list_ingredients = []
        for ingredient in serialized_ingredients.data:

            # get the item object for the ingredient
            item_id = ingredient['itemID']
            item_from_db = Item.objects.get(id=item_id)

            # get the quantity and unit for the ingredient
            quantity = ingredient['quantity']
            unit_name = ""
            if ingredient['unitID']:
                unit_id = ingredient['unitID']
                unit_from_db = Unit.objects.get(id=unit_id)
                unit_name = unit_from_db.name
            else:
                unit_name = None

            # get the order number for the ingredient
            order_id = ingredient['orderNumber']

            # add the ingredient with all the data to the list of ingredients
            list_ingredients.append(
                {
                    'name': item_from_db.name,
                    'quantity': quantity,
                    'unit': unit_name,
                    'orderID': order_id
                }
            )

        # return the list of ingredients
        return Response(list_ingredients, status=status.HTTP_200_OK)
    else:
        # return an error response if the request method is not POST
        return JsonResponse({'error': 'this API is POST API'}, status=405)


@api_view(['POST'])
def get_recipe_steps(request):
    if request.method == 'POST':

        # load request body data into JSON object
        data = json.loads(request.body)

        # retrieve recipe ID from data and convert to UUID object
        recipe_id = UUID(data['RecipeID'])

        # query Recipe object with given ID and retrieve recipe object
        recipe = Recipe.objects.get(pk=recipe_id)

        # query Step objects related to recipe and serialize with StepSerializer
        steps = Step.objects.filter(recipe=recipe)
        serialized_steps = StepSerializer(steps, many=True)

        # create list of dictionaries containing step descriptions and order IDs
        list_steps = []
        for step in serialized_steps.data:
            step_description = step['description']
            step_order_id = step['orderID']
            list_steps.append(
                {
                    'description': step_description,
                    'orderID': step_order_id,
                }
            )

        # return list of steps as response with 200 OK status
        return Response(list_steps, status=status.HTTP_200_OK)
    else:
        # return error response if request method is not POST
        return JsonResponse({'error': 'this API is POST API'}, status=405)


# Home Screen APIs ################################

@api_view(['GET'])
def get_all_editors_choice_recipes(request):
    if request.method == 'GET':
        # retrieve all editor's choice recipes from the Recipe model in the database
        # annotate each recipe with a new field orderIDNEW that represents its row number
        editors_choice_recipes = Recipe.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
                order_by=F('orderID').asc()
            )
        ).filter(isEditorChoice=True).order_by('orderID').exclude(orderID__isnull=True).values(
            'id', 'videoUrl', 'videoTitle', 'videoImage', 'title', 'time', 'pictureUrl', 'isEditorChoice', 'orderIDNEW')

        new_list_of_editors_choice_recipes = []

        for recipe in editors_choice_recipes:
            # create a new dictionary for video data
            video_data = {
                'youtubeLink': recipe['videoUrl'],
                'title': recipe['videoTitle'],
                'channelName': recipe['videoChannelName'],
                'image': recipe['videoImage'],
                'duration': recipe['videoDuration']
            }

            # create a new dictionary for the recipe data
            recipe_data = {
                'id': recipe['id'],
                'name': recipe['title'],
                'time': recipe['time'],
                'pictureUrl': recipe['pictureUrl'],
                'videoUrl': video_data,
                'isEditorChoice': recipe['isEditorChoice'],
                'orderID': recipe['orderIDNEW']
            }

            # Add the new recipe data to the list
            new_list_of_editors_choice_recipes.append(recipe_data)

        # Return the list of new recipe data as a response with HTTP status code 200
        return Response(new_list_of_editors_choice_recipes, status=status.HTTP_200_OK)
    else:
        # If the request method is not GET, return an error response with HTTP status code 405
        return JsonResponse({'error': 'this API is POST API'}, status=405)


@api_view(['POST'])
def select_shopping_list_in_home_screen(request):
    if request.method == 'POST':
        # extract the data from the request body
        data = json.loads(request.body)
        category_id = data['categoryID']
        user_id = data['userID']

        # check if categoryID is provided
        if not category_id:
            return Response({"error": "categoryID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # get the ShoppingListCategory object using the categoryID
        try:
            shopping_list_category = ShoppingListCategory.objects.get(pk=category_id)
        except ShoppingListCategory.DoesNotExist:
            return Response({"error": f"Category with ID {category_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # check if userID is provided
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # get the User object using the userID
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # get the shopping list name and id
        shopping_list_name = shopping_list_category.name
        shopping_list_id = shopping_list_category.id

        # update the user's selected shopping list to the categoryID and save
        user.selectedShoppingList = str(category_id)
        user.save()

        # get the shopping list items for the given shopping list category
        list_items = ShoppingListItem.objects.annotate(
            orderNumberNEW=Window(
                expression=RowNumber(),
                order_by=F('orderNumber').asc()
            )
        ).filter(categoryID=shopping_list_category).order_by('orderNumber')

        # exclude items that do not have an orderNumber and get the item ID,
        # check status, and order number for each item
        list_items = list_items.exclude(orderNumber__isnull=True).values('id', 'itemID', 'isCheck', 'orderNumberNEW')

        new_list_of_items = []

        # loop through the list_items and get the name of the item from the Item table
        for shopping_list_item in list_items:
            item_id = shopping_list_item['itemID']
            item_from_db = Item.objects.get(id=item_id)

            # append the item information to the new list of items
            new_list_of_items.append(
                {
                    'id': shopping_list_item['id'],
                    'name': item_from_db.name,
                    'isCheck': shopping_list_item['isCheck'],
                    'orderID': shopping_list_item['orderNumberNEW']
                }
            )

            # stop the loop at the fourth item
            if shopping_list_item['orderNumberNEW'] == 4:
                break

        # create the shopping list category data object
        category_data = {
            "shoppingListCategoryID": str(shopping_list_id),
            "shoppingListCategoryName": shopping_list_name,
            "listOfItems": new_list_of_items,
        }

        # return the shopping list category data as a JSON response with a success status
        return JsonResponse(category_data, status=status.HTTP_200_OK)
    else:
        # if the request method is not POST, return a message indicating that this is a POST API with an error status
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_home_screen_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data['userID']

        # check if user id sent
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # get the id of selected shopping list of user
        selected_shopping_list_id = user.selectedShoppingList

        # check if selected_shopping_list_id if its null or empty
        if selected_shopping_list_id is None or selected_shopping_list_id == "":
            returned_shopping_list = None
            print("no selected shopping list ")
        try:
            shopping_list_category = ShoppingListCategory.objects.get(pk=selected_shopping_list_id)

            # get 4 items of shopping list
            shopping_list_items = ShoppingListItem.objects.annotate(
                orderNumberNEW=Window(
                    expression=RowNumber(),
                    order_by=F('orderNumber').asc()
                )
            ).filter(categoryID=shopping_list_category).order_by('orderNumber')
            shopping_list_items = shopping_list_items.exclude(orderNumber__isnull=True).values('id', 'itemID',
                                                                                               'isCheck',
                                                                                               'orderNumberNEW')

            new_list_of_items = []
            for shopping_list_item in shopping_list_items:
                # get name of Item using ItemID
                item_id = shopping_list_item['itemID']
                item_from_db = Item.objects.get(id=item_id)
                new_list_of_items.append(
                    {
                        'id': shopping_list_item['id'],
                        'name': item_from_db.name,
                        'isCheck': shopping_list_item['isCheck'],
                        'orderID': shopping_list_item['orderNumberNEW']
                    }
                )
                if shopping_list_item['orderNumberNEW'] == 4:
                    break

            returned_shopping_list = {
                "ShoppingListName": shopping_list_category.name,
                "items": new_list_of_items
            }
        except ShoppingListCategory.DoesNotExist:
            print("selected shopping list is deleted")
            returned_shopping_list = None

        # retrieve the four newest recipes for the user and sort them by the date they were added
        recently_added_recipes = Recipe.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
            )
        ).filter(userID=user_id).order_by('-dateAdded').exclude(orderID__isnull=True)[:4].values(
            'id', 'videoUrl', 'videoTitle', 'videoImage', 'title', 'time', 'pictureUrl', 'isEditorChoice', 'orderIDNEW')

        returned_recently_recipe_added = []
        order = 1
        for recipe in recently_added_recipes:
            video_data = {
                'youtubeLink': recipe['videoUrl'],
                'title': recipe['videoTitle'],
                'image': recipe['videoImage'],
            }
            recipe_data = {
                'id': recipe['id'],
                'name': recipe['title'],
                'time': recipe['time'],
                'pictureUrl': recipe['pictureUrl'],
                'videoUrl': video_data,
                'isEditorChoice': recipe['isEditorChoice'],
                'orderID': order
            }
            returned_recently_recipe_added.append(recipe_data)
            order += 1

        returned_data = {
            "recentlyAdded": returned_recently_recipe_added,
            "selectedShoppingList": returned_shopping_list
        }

        return Response(returned_data, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


# WebExtension APIs ################################

@api_view(['POST'])
def save_recipe(request):
    # global item_from_db, unit_from_db
    if request.method == 'POST':
        recipe_data = request.body
        # Print the request body to the terminal
        print(recipe_data)
        try:
            # Parse the request body

            try:
                data = json.loads(request.body)
            except Exception as e:
                return JsonResponse({'error': f'Error occurred while processing text: {e}.'}, status=405)
            category_id = UUID(data['recipeCategoryID'])
            recipe_name = data['name']
            time = data['time']
            picture_url = data['pictureUrl']
            is_editor_choice = data['isEditorChoice']
            ingredients = data['ingredients']
            steps = data['steps']
            user_id = data['userID']
            add_to_shopping_list = data['addToShoppingList']
            shopping_list_category_id = data['shoppingListCategoryID']

            if add_to_shopping_list:
                if not shopping_list_category_id or shopping_list_category_id is None or shopping_list_category_id == "":
                    return Response({"error": "shoppingListCategoryID is required."}, status=status.HTTP_400_BAD_REQUEST)

            # check anf get user object from DB
            if not user_id:
                return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                user = User.objects.get(pk=user_id)
            except:
                return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

            if not category_id:
                return Response({"error": "category_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                category = RecipeCategory.objects.get(pk=category_id)
            except:
                return Response({"error": f"category with ID {category_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

            video_data = get_video(recipe_name)
            video_url = video_data['youtubeLink']
            video_image = video_data['image']
            video_title = video_data['title']
            video_duration = video_data['duration']
            video_channel_name = video_data['channelName']
            video_published_date = video_data['videoPostedDate']

            # Get existing recipes in the same category
            existing_recipes = Recipe.objects.filter(category=category)

            # Set the orderID for the new recipe
            order_id = len(existing_recipes) + 1
            recipe = Recipe(id=uuid4(),
                            title=recipe_name,
                            time=time,
                            pictureUrl=picture_url,
                            videoUrl=video_url,
                            videoImage=video_image,
                            videoTitle=video_title,
                            videoDuration=video_duration,
                            videoChannelName=video_channel_name,
                            videoPostedDate=video_published_date,
                            isEditorChoice=is_editor_choice,
                            category=category,
                            userID=user,
                            orderID=order_id
                            )
            recipe.save()

            for ingredient in ingredients:
                item_name = ingredient['name']
                if 'quantity' not in ingredient:
                    ingredient['quantity'] = ""
                else:
                    quantity = ingredient['quantity']
                if 'unit' not in ingredient:
                    unit_name = ""
                else:
                    unit_name = ingredient['unit']
                order_id = ingredient['orderID']
                try:
                    item_from_db = Item.objects.get(name=item_name)
                    item = item_from_db
                except Item.DoesNotExist:
                    items_length = Item.objects.count()
                    item = Item(id=items_length + 1, name=item_name)
                    item.save()

                if add_to_shopping_list:
                    temp_category = ShoppingListCategory.objects.get(pk=shopping_list_category_id)
                    is_check = False
                    shopping_list_items = ShoppingListItem.objects.filter(categoryID=temp_category)
                    order_number = len(shopping_list_items) + 1
                    shopping_list_item = ShoppingListItem(
                        id=uuid4(),
                        itemID=item,
                        categoryID=temp_category,
                        isCheck=is_check,
                        orderNumber=order_number
                    )
                    shopping_list_item.save()


                if unit_name:
                    try:
                        unit_from_db = Unit.objects.get(name=unit_name)
                        unit = unit_from_db
                    except Unit.DoesNotExist:
                        unit_length = Unit.objects.count()
                        unit = Unit(id=unit_length + 1, name=unit_name)
                        unit.save()
                else:
                    unit = None

                ingredient_id = uuid4()
                # Create the ingredient instance
                ingredient = Ingredient(id=ingredient_id, itemID=item, quantity=quantity, unitID=unit,
                                        recipe=recipe, orderNumber=order_id)
                ingredient.save()

            # Loop over the steps and create their related models
            for step in steps:
                description = step['description']
                order_id = step['orderID']

                # Create the step instance
                step = Step(id=uuid4(), description=description, orderID=order_id, recipe=recipe)
                step.save()

            # Return a success response
            return JsonResponse({'message': 'Recipe saved successfully.'}, status=201)

        except (KeyError, ValueError, TypeError, RecipeCategory.DoesNotExist, Item.DoesNotExist):
            # Return an error response if the request is not properly formatted or the category or item do not exist
            return JsonResponse({'error': ValueError}, status=400)

    # Return an error response if the request method is not POST
    return JsonResponse({'error': 'this API is POST API'}, status=405)


# this api used in save_recipe api to get the video from you-tube that have max number of views
def get_video(query):
    # set the API key
    api_key = 'AIzaSyCi6S6uY5QpEI8MRZ7z2VJTH69sOI_SMuM'

    # build the YouTube API client
    youtube = build('youtube', 'v3', developerKey=api_key)

    try:
        # search for videos matching the query, sorted by view count in descending order
        search_response = youtube.search().list(
            q=query + ' recipe',
            type='video',
            part='id',
            maxResults=30,
            order='viewCount',
            fields='items(id(videoId))'
        ).execute()

        # extract the video IDs from the search results
        video_ids = [search_result['id']['videoId'] for search_result in search_response['items']]

        # retrieve video information (title, thumbnail, view count) for the matching videos
        video_info = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids),
            fields='items(id,snippet(channelTitle,title,thumbnails/high/url,publishedAt),statistics(viewCount),contentDetails(duration))'
        ).execute()

    except HttpError as error:
        print('An error occurred: %s' % error)

    # initialize variables for tracking the video with the most views
    max_views = 0
    link_of_max_views = ""
    title_of_max_views = ""
    image_of_max_views = ""
    duration_of_max_views = ""
    channel_of_max_views = ""
    published_date_of_max_views = ""

    # loop through the retrieved video information to find the video with the most views
    for video_result in video_info['items']:
        video_id = video_result['id']
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        views = video_result['statistics']['viewCount']
        title = video_result['snippet']['title']
        thumbnail_url = video_result['snippet']['thumbnails']['high']['url']
        duration = video_result['contentDetails']['duration']
        channel_title = video_result['snippet']['channelTitle']
        published_date = datetime.strptime(video_result['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%S%z').strftime('%b %d, %Y')

        # convert the duration to a more readable format (e.g. "PT5M23S" -> "5:23")
        duration = re.sub('[^0-9a-zA-Z]+', '', duration)  # remove non-alphanumeric characters
        duration = duration.lower()
        duration = duration.replace('pt', '')
        duration = duration.replace('h', ':').replace('m', ':').replace('s', '')
        if duration.startswith(':'):
            duration = duration[1:]

        # update the variables tracking the video with the most views if this video has more views
        if int(views) > int(max_views):
            max_views = views
            link_of_max_views = video_url
            title_of_max_views = title
            image_of_max_views = thumbnail_url
            duration_of_max_views = duration
            channel_of_max_views = channel_title
            published_date_of_max_views = published_date

    # create a dictionary with the information about the video with the most views
    data = {
        'youtubeLink': link_of_max_views,
        'title': title_of_max_views,
        'image': image_of_max_views,
        'duration': duration_of_max_views,
        'channelName': channel_of_max_views,
        'videoPostedDate': str(published_date_of_max_views)
    }

    # return the dictionary
    return data


@api_view(['POST'])
def get_recipe_information_web_extension(request):
    if request.method == 'POST':
        try:
            # extracts website URL and user ID from the request body and loads it as JSON
            data = json.loads(request.body)
            website_url = data['websiteUrl']
            user_id = data['userID']

            try:
                # attempts to get the user with the given ID from the database
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

            # fetches recipe categories for the given user and orders them by orderID
            categories = RecipeCategory.objects.filter(user=user).order_by('orderID')

            # serializes the categories data
            serializer = RecipeCategorySerializer(categories, many=True)

            # scrapes the website for recipe information
            scraper = scrape_me(website_url)

            ingredients = []
            steps = []

            # extracts ingredients from the scraped recipe and formats them as a list
            for ingredient in scraper.ingredients():

                # parses the quantity and unit of the ingredient using a natural language processing library
                quants = parser.parse(ingredient)
                if quants.__len__() == 0:
                    quantity = None
                    unit = None
                else:
                    quantity = quants[0].value
                    unit = quants[0].unit.name

                if unit == 'dimensionless':
                    unit = None

                # normalizes the ingredient name by converting fractions to decimal values
                ingredient_parce_name = parse(convert_fraction(ingredient))
                if ',' in ingredient_parce_name['name']:
                    ingredient_parce_name = ingredient_parce_name['name'].split(',')[0]
                else:
                    ingredient_parce_name = ingredient_parce_name['name']

                # adds the formatted ingredient to the list
                ingredients.append(
                    {
                        'name': ingredient_parce_name,
                        'quantity': quantity,
                        'unit': unit,
                        'orderID': -1
                    }
                )

            # extracts recipe steps from the scraped recipe and formats them as a list
            for step in scraper.instructions_list():
                steps.append(
                    {
                        'description': step,
                        'orderID': -1
                    }
                )

            try:
                # attempts to extract the cook time from the scraped recipe
                time = scraper.cook_time()
            except:
                # sets cook time to None if it couldn't be extracted
                time = None

            # Formats the scraped recipe data into a dictionary
            recipe_data = {
                'name': scraper.title(),
                'time': time,
                'pictureUrl': scraper.image(),
                'isEditorChoice': False,
                'ingredients': ingredients,
                'steps': steps
            }

            # Combines the recipe data and category data into a single dictionary
            all_data = {
                'recipe': recipe_data,
                "categories": serializer.data
            }
            # Returns the combined data as a JSON response with a 201 status code
            return Response(all_data, status=status.HTTP_201_CREATED, )
        except:
            # Returns a bad request response if the scraping failed
            return HttpResponseBadRequest("Scraping not supported for this URL")
    else:
        # Return an error response if the request method is not POST
        return JsonResponse({'error': 'this API is POST API'}, status=405)


# this api used to convert the fractions in ingredients of recipe
def convert_fraction(string):
    if '½' in string:
        fraction = unicodedata.numeric('½')
        string = string.replace('½', str(fraction))
    elif '¼' in string:
        fraction = unicodedata.numeric('¼')
        string = string.replace('¼', str(fraction))
    elif '¾' in string:
        fraction = unicodedata.numeric('¾')
        string = string.replace('¾', str(fraction))
    return string


# WebExtension APIs ################################


@api_view(['POST'])
def generate_recipe_ocr(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data['text']
        user_id = data['userID']
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        categories = RecipeCategory.objects.filter(user=user).order_by('orderID')
        serialized_categories = RecipeCategorySerializer(categories, many=True)

        recipe = generate_recipe(text)
        recipe_result = recipe.split('\n\n')
        recipe_result = recipe_result[1]
        recipe_dict = json.loads(recipe_result)
        recipe_name = recipe_dict['recipeData']['name']
        ingredients = recipe_dict['recipeData']['ingredients']
        steps = recipe_dict['recipeData']['steps']
        time = recipe_dict['recipeData']['time']

        # Create JSON model
        recipe_model = {
            "name": recipe_name,
            "time": time,
            "pictureUrl": None,
            "isEditorChoice": False,
            "ingredients": [],
            "steps": []
        }
        for ingredient in ingredients:
            ingredient_model = {
                "name": ingredient["name"],
                "quantity": None if ingredient["quantity"] == "" or ingredient["quantity"] == "none" else ingredient["quantity"],
                "unit": None if ingredient["unit"] == "" else ingredient["unit"],
                "orderID": -1
            }
            recipe_model["ingredients"].append(ingredient_model)

        for step in steps:
            recipe_model["steps"].append({
                "description": step["step"],
                "orderID": -1
            })

        final_data = {
            "recipe": recipe_model,
            "categories": serialized_categories.data,
        }
        return Response(final_data, status=status.HTTP_201_CREATED, )
    else:
        return JsonResponse({'error': 'Invalid request method'})


def generate_recipe(text):
    prompt = f"""Extract the recipe data in json format like this {{{{"recipeData": {{"name": "string", 
    "time": "int and nullable in minutes " "ingredients": [{{"name": "string","quantity": 1.1,"unit": "string"}}],
    "steps": [{{"step": "string",}}]}}}}}} from this text: {text}. and set \n between 2 lines"""
    try:
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )
    except Exception as e:
        print(f'error : {e}')
    recipe = response.choices[0].text
    return recipe


# Shopping list category functionality APIs ################################

@api_view(['POST'])
def create_shopping_list_category(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # reformat the data
        category_uuid = uuid4()
        name = data['name']
        icon = data['icon']
        user_id = data['userID']
        temp_user = User.objects.get(pk=user_id)
        shopping_list_categories = ShoppingListCategory.objects.filter(user=temp_user).order_by('orderID')
        order_id = len(shopping_list_categories) + 1

        temp_category = ShoppingListCategory(
            id=category_uuid,
            name=name,
            orderID=order_id,
            user=temp_user,
            icon=icon
        )

        temp_category.save()
        serialized_category = ShoppingListCategorySerializer(temp_category)
        return JsonResponse(serialized_category.data, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def delete_shopping_list_category(request):
    if request.method == 'POST':
        category_id = request.data.get('id')
        category = get_object_or_404(ShoppingListCategory, id=category_id)
        category.delete()
        return Response({'message': ' Shopping list Category deleted :( '}, status=status.HTTP_204_NO_CONTENT)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def rename_shopping_list_category(request):
    if request.method == 'POST':
        category_id = request.data.get('id')
        new_name = request.data.get('newName')
        category = get_object_or_404(ShoppingListCategory, id=category_id)
        category.name = new_name
        category.save()
        serializer = RecipeCategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_all_shopping_list_categories(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data['userID']

        # check if user ID is available
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # create query set that get categories from DB
        categories = ShoppingListCategory.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
                order_by=F('orderID').asc()
            )
        ).filter(user=user).order_by('orderID')

        # reformat the data in JSON format
        list_of_categories = []
        for category in categories:
            temp_category = ShoppingListCategory.objects.get(pk=category.id)
            items = ShoppingListItem.objects.filter(categoryID=temp_category)
            length = len(items)
            # put all data of each Shopping list category
            list_of_categories.append(
                {
                    'id': category.id,
                    'name': category.name,
                    'icon': category.icon,
                    'numberOfItems': length,
                    'orderID': category.orderIDNEW,
                }
            )

        # return all Shopping list categories with theme items
        return Response(list_of_categories, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


# Shopping list item functionality APIs ################################

@api_view(['POST'])
def get_shopping_list_items(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = data['categoryID']

        # check if category ID is available
        if not category_id:
            return Response({"error": "categoryID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            shopping_list_category = ShoppingListCategory.objects.get(pk=category_id)
        except ShoppingListCategory.DoesNotExist:
            return Response({"error": f"Category with ID {category_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        items = ShoppingListItem.objects.annotate(
            orderNumberNEW=Window(
                expression=RowNumber(),
                order_by=F('orderNumber').asc()
            )
        ).filter(categoryID=shopping_list_category).order_by('orderNumber')
        items = items.exclude(orderNumber__isnull=True).values('id', 'itemID', 'isCheck', 'orderNumberNEW')

        new_list_of_items = []
        for shopping_list_item in items:
            # get name of Item using ItemID
            item_id = shopping_list_item['itemID']
            item_from_db = Item.objects.get(id=item_id)
            new_list_of_items.append(
                {
                    'id': shopping_list_item['id'],
                    'name': item_from_db.name,
                    'isCheck': shopping_list_item['isCheck'],
                    'orderID': shopping_list_item['orderNumberNEW']
                }
            )

        return Response(new_list_of_items, status=status.HTTP_200_OK)

    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def add_new_shopping_list_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_uuid = uuid4()
        shopping_list_item_name = data['name']
        category_id = data['categoryID']
        temp_category = ShoppingListCategory.objects.get(pk=category_id)
        is_check = False
        shopping_list_items = ShoppingListItem.objects.filter(categoryID=temp_category)
        order_number = len(shopping_list_items) + 1

        try:
            item_from_db = Item.objects.get(name=shopping_list_item_name)
            item = item_from_db
        except Item.DoesNotExist:
            items_length = Item.objects.count()
            item = Item(id=items_length + 1, name=shopping_list_item_name)
            item.save()

        shopping_list_item = ShoppingListItem(
            id=item_uuid,
            itemID=item,
            categoryID=temp_category,
            isCheck=is_check,
            orderNumber=order_number
        )
        shopping_list_item_info = {
            "id": item_uuid,
            "name": shopping_list_item_name,
            "isCheck": is_check,
            "orderID": order_number
        }
        shopping_list_item.save()
        return JsonResponse(shopping_list_item_info, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def delete_shopping_list_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        shopping_list_item_id = data['itemID']
        try:
            shopping_list_item = ShoppingListItem.objects.get(pk=shopping_list_item_id)
        except:
            return JsonResponse({'message': 'shopping list item not found'}, status=status.HTTP_400_BAD_REQUEST)

        shopping_list_item.delete()
        return Response({'message': ' shopping list item deleted :( '}, status=status.HTTP_204_NO_CONTENT)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def toggle_items_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_ids = data.get('itemIDs', [])
        for item_id in item_ids:
            item = ShoppingListItem.objects.get(pk=item_id)
            item.isCheck = not item.isCheck
            item.save()
        return JsonResponse({'message': 'items status updated successfully'}, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


def get_lat_lon_from_google_maps_link(link):
    # extract the place ID from the link
    place_id_list = re.findall(r'place/([\w\d]+)', link)
    if not place_id_list:
        raise ValueError("Link doesn't contain a place ID.")
    place_id = place_id_list[0]

    # request the place details from the Google Maps API
    response = requests.get(f'https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key=<your_api_key>')

    # extract the latitude and longitude from the response
    lat = response.json()['result']['geometry']['location']['lat']
    lon = response.json()['result']['geometry']['location']['lng']

    return lat, lon


def extract_lat_lon(gmaps_link):
    """
    Extract latitude and longitude from a Google Maps link.
    """
    url = gmaps_link
    lat_lon_regex = re.compile(r'\/@([-+]?\d*\.\d+),([-+]?\d*\.\d+)')
    match = lat_lon_regex.search(url)
    print(match)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon
    else:
        return JsonResponse({'error': 'No match found'})

# markets in Whisk App functionality  APIs ################################


@api_view(['POST'])
def check_availability(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # get the list of items names from the request
        names = data['listOfItemsNames']
        # get the user's latitude and longitude from the request
        user_lat = float(data['userLat'])
        user_lon = float(data['userLon'])

        # Convert all names to lowercase

        lower_names = [name.lower() for name in names]

        # get the list of items and markets
        items = Item.objects.filter(name__in=lower_names)
        markets = Market.objects.all()

        # get the list of available items for each market
        market_items = []
        for market in markets:

            items_available = MarketItem.objects.filter(marketID=market, itemID__in=items)

            item_names_available = list(items_available.values_list('itemID__name', flat=True))

            available_items = [(name.lower(), name.lower() in [item.lower() for item in item_names_available]) for name
                               in names]

            list_of_available_items = []
            i = 0
            for lower_name in lower_names:
                list_of_available_items.append(
                    {
                        "itemName": names[i],
                        "isAvailable": lower_name in [item.lower() for item in item_names_available],
                    }
                )
                i += 1

            item_ids = [item.itemID_id for item in items_available]
            num_available = len(item_ids)
            market_lat, market_lon = extract_lat_lon(market.location)

            # set connection with go-ogle api using api key
            gmaps_client = googlemaps.Client(key='AIzaSyBTSe2uK5-e9aS35lkm5sz_y3z3AF67H0w')
            source = f'{user_lat},{user_lon}'
            destination = f'{market_lat},{market_lon}'

            # get all info distance matrix
            direction_result = gmaps_client.directions(source,
                                                       destination,
                                                       mode="driving",
                                                       avoid="ferries",
                                                       departure_time=datetime.now(),
                                                       transit_mode='car')

            dist = direction_result[0]['legs'][0]['distance']
            dist = dist['text']

            # add new market object
            market_items.append({
                'marketName': market.name,
                'marketLogo': market.logo,
                'marketLat': str(market_lat),
                'marketLon': str(market_lon),
                'locationLink': market.location,
                'distance': dist,
                'numAvailableItems': num_available,
                'availableItems': list_of_available_items
            })

        # return the list of available items for each market as a JSON response
        return Response(market_items, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)



# Apis Just for testing :

@api_view(['GET'])
def send_name(request, name):
    if request.method == 'GET':
        return JsonResponse({"name": name})
    else:
        return HttpResponseBadRequest("Bad Request: Only GET requests are allowed")