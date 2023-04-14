import unicodedata
from datetime import datetime
import googlemaps
from django.db.models import Window
from django.db.models import F
from django.db.models.functions import RowNumber
from googleapiclient.errors import HttpError
from rest_framework.generics import get_object_or_404
from .serializer import IngredientSerializer, RecipeCategorySerializer, StepSerializer, \
    UserSerializer, ShoppingListCategorySerializer, ShoppingListItemSerializer
from .models import User, Recipe, Ingredient, Step, RecipeCategory, Unit, Item, ShoppingListCategory, ShoppingListItem, \
    Market, MarketItem
from pytube import YouTube
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


@api_view(['POST'])
def create_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = User(
            id=data['userID'],
            firstName=data['firstName'],
            lastName=data['lastName'],
            phoneNumber=data['phoneNumber'],
            age=data['age'],
            weight=data['weight'],
            height=data['height'],
        )
        user.save()
        serialized_user = UserSerializer(user)
        return JsonResponse(serialized_user.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def add_recipe(request):
    recipe_name = request.data['recipe_name']
    user_id = request.data['user_id']

    # Retrieve the user object from the database
    user = User.objects.get(id=user_id)

    # Retrieve the serialized string from the recentlyRecipesAdded field and convert it to a list
    serialized_list = user.recentlyRecipesAdded
    if serialized_list:
        recipe_list = serialized_list.split(',')
    else:
        recipe_list = []

    # Append the new recipe to the end of the list and remove the first element if the length of the list exceeds 4
    recipe_list.append(recipe_name)
    if len(recipe_list) > 4:
        recipe_list.pop(0)

    # Serialize the updated list back to a string and save it in the recentlyRecipesAdded field
    updated_serialized_list = ','.join(recipe_list)
    user.recentlyRecipesAdded = updated_serialized_list
    user.save()

    return Response({'list': user.recentlyRecipesAdded})








@api_view(['POST'])
def update_user_data(request):
    if request.method == 'POST':
        user_id = request.data.get('id')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def create_recipe_category(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # reformat the data
        category_uuid = uuid4()
        name = data['name']
        user_id = data['userID']
        temp_user = User.objects.get(pk=user_id)
        categories = RecipeCategory.objects.filter(user=temp_user).order_by('orderID')
        order_id = len(categories) + 1

        temp_category = RecipeCategory(
            id=category_uuid,
            name=name,
            orderID=order_id,
            user=temp_user
        )

        temp_category.save()
        serialized_category = RecipeCategorySerializer(temp_category)
        return JsonResponse(serialized_category.data, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def rename_recipe_category(request):
    if request.method == 'POST':
        category_id = request.data.get('id')
        new_name = request.data.get('newName')
        category = get_object_or_404(RecipeCategory, id=category_id)
        category.name = new_name
        category.save()
        serializer = RecipeCategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def delete_recipe_category(request):
    if request.method == 'POST':
        category_id = request.data.get('id')
        category = get_object_or_404(RecipeCategory, id=category_id)
        category.delete()
        return Response({'message': ' Recipe Category deleted :( '}, status=status.HTTP_204_NO_CONTENT)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def delete_recipe(request):
    if request.method == 'POST':
        recipe_id = request.data.get('id')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        recipe.delete()
        return Response({'message': ' Recipe deleted :( '}, status=status.HTTP_204_NO_CONTENT)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_all_recipe_categories(request):
    if request.method == 'POST':
        user_id = request.data.get('userID')
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=user_id)
        except:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        categories = RecipeCategory.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
                order_by=F('orderID').asc()
            )
        ).filter(user=user_id).order_by('orderID')
        categories = categories.exclude(orderID__isnull=True).values('id', 'name', 'orderIDNEW')

        list_data = []
        for category in categories:
            recipes_of_this_category = Recipe.objects.filter(category=category['id'])
            list_data.append(
                {
                    'id': category['id'],
                    'name': category['name'],
                    'orderID': category['orderIDNEW'],
                    'numOfRecipes': len(recipes_of_this_category)
                }
            )

        data = list(categories.values())
        # qs_json = serializers.Serializer(categories)
        return Response(list_data, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_all_recipes(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = UUID(data['categoryID'])
        if not category_id:
            return Response({"error": "categoryID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            category = RecipeCategory.objects.get(pk=category_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {category_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        recipes = Recipe.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
                order_by=F('orderID').asc()
            )
        ).filter(category=category).order_by('orderID').exclude(orderID__isnull=True).values('id', 'videoUrl',
                                                                                             'videoTitle', 'videoImage',
                                                                                             'title', 'time',
                                                                                             'pictureUrl',
                                                                                             'is_editor_choice',
                                                                                             'orderIDNEW')
        new_list_of_recipes = []

        for recipe in recipes:
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
                'isEditorChoice': recipe['is_editor_choice'],
                'orderID': recipe['orderIDNEW']
            }
            new_list_of_recipes.append(recipe_data)

        return Response(new_list_of_recipes, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)


@api_view(['POST'])
def get_recipe_ingredients(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        recipe_id = UUID(data['RecipeID'])
        recipe = Recipe.objects.get(pk=recipe_id)

        ingredients = Ingredient.objects.filter(recipe=recipe)
        serialized_ingredients = IngredientSerializer(ingredients, many=True)

        list_ingredients = []
        for ingredient in serialized_ingredients.data:

            item_id = ingredient['itemID']
            item_from_db = Item.objects.get(id=item_id)

            quantity = ingredient['quantity']

            unit_name = ""
            if ingredient['unitID']:
                unit_id = ingredient['unitID']
                unit_from_db = Unit.objects.get(id=unit_id)
                unit_name = unit_from_db.name
            else:
                unit_name = None

            order_id = ingredient['orderNumber']

            list_ingredients.append(
                {
                    'name': item_from_db.name,
                    'quantity': quantity,
                    'unit': unit_name,
                    'orderNumber': order_id
                }
            )

        return Response(list_ingredients, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)


@api_view(['POST'])
def get_recipe_steps(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        recipe_id = UUID(data['RecipeID'])
        recipe = Recipe.objects.get(pk=recipe_id)

        steps = Step.objects.filter(recipe=recipe)
        serialized_steps = StepSerializer(steps, many=True)

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

        return Response(list_steps, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)


@api_view(['POST'])
def save_recipe_two(request):
    # global item_from_db, unit_from_db
    if request.method == 'POST':
        try:
            # Parse the request body
            data = json.loads(request.body)
            category_id = UUID(data['categoryID'])
            recipe_name = data['name']
            time = data['time']
            picture_url = data['pictureUrl']
            video_url = data['videoUrl']['youtubeLink']
            video_image = data['videoUrl']['image']
            video_title = data['videoUrl']['title']
            is_editor_choice = data['isEditorChoice']
            ingredients = data['ingredients']
            steps = data['steps']

            # Check if the category exists in the database
            category = RecipeCategory.objects.get(pk=category_id)

            # Get existing recipes in the same category
            existing_recipes = Recipe.objects.filter(category=category)

            # Set the orderID for the new recipe
            order_id = len(existing_recipes) + 1
            recipe = Recipe(id=uuid4(), title=recipe_name, time=time, pictureUrl=picture_url,
                            videoUrl=video_url, videoImage=video_image, videoTitle=video_title,
                            is_editor_choice=is_editor_choice, category=category, orderID=order_id)
            recipe.save()

            for ingredient in ingredients:
                item_name = ingredient['name']
                quantity = ingredient['quantity']
                unit_name = ingredient['unit']
                order_id = ingredient['orderID']
                try:
                    item_from_db = Item.objects.get(name=item_name)
                    item = item_from_db
                except Item.DoesNotExist:
                    items_length = Item.objects.count()
                    item = Item(id=items_length + 1, name=item_name)
                    item.save()
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
                description = step['name']
                order_id = step['orderID']

                # Create the step instance
                step = Step(id=uuid4(), description=description, orderID=order_id, recipe=recipe)
                step.save()

            # Return a success response
            return JsonResponse({'message': 'Recipe saved successfully.'}, status=201)

        except (KeyError, ValueError, TypeError, RecipeCategory.DoesNotExist, Item.DoesNotExist):
            # Return an error response if the request is not properly formatted or the category or item do not exist
            return JsonResponse({'error': 'Invalid request.'}, status=400)

    # Return an error response if the request method is not POST
    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@api_view(['POST'])
def get_recipe_information_web_extension(request):
    try:
        data = json.loads(request.body)
        website_url = data['websiteUrl']
        user_id = data['userID']
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)
        categories = RecipeCategory.objects.filter(user=user).order_by('orderID')
        serializer = RecipeCategorySerializer(categories, many=True)

        scraper = scrape_me(website_url)

        ingredients = []

        steps = []

        for ingredient in scraper.ingredients():
            quants = parser.parse(ingredient)
            if quants.__len__() == 0:
                quantity = None
                unit = ""
            else:
                quantity = quants[0].value
                unit = quants[0].unit.name

            if unit == 'dimensionless':
                unit = None

            ingredient_parce_name = parse(convert_fraction(ingredient))
#ss
            ingredients.append(
                {
                    'name': ingredient_parce_name['name'],
                    'quantity': quantity,
                    'unit': unit,
                    'orderID': -1
                }
            )


        for step in scraper.instructions_list():
            steps.append(
                {
                    'name': step,
                    'orderID': -1
                }
            )

        recipe_data = {
            'name': scraper.title(),
            'time': scraper.total_time(),
            'pictureUrl': scraper.image(),
            'videoUrl': get_video(scraper.title()),
            'isEditorChoice': False,
            'ingredients': ingredients,
            'steps': steps
        }

        all_data = {
            'recipe': recipe_data,
            "categories": serializer.data
        }
        return Response(all_data, status=status.HTTP_201_CREATED, )
    except:
        return HttpResponseBadRequest("Scraping not supported for this URL")


def get_video(query):
    # Set the API key
    api_key = 'AIzaSyCi6S6uY5QpEI8MRZ7z2VJTH69sOI_SMuM'

    # Build the YouTube API client
    youtube = build('youtube', 'v3', developerKey=api_key)

    try:
        # Search for videos matching the query, sorted by view count in descending order
        search_response = youtube.search().list(
            q=query + ' recipe',
            type='video',
            part='id',
            maxResults=30,
            order='viewCount',
            fields='items(id(videoId))'
        ).execute()

        # Extract the video IDs from the search results
        video_ids = [search_result['id']['videoId'] for search_result in search_response['items']]

        # Retrieve video information (title, thumbnail, view count) for the matching videos
        video_info = youtube.videos().list(
            part='snippet,statistics',
            id=','.join(video_ids),
            fields='items(id,snippet(title,thumbnails/high/url),statistics(viewCount))'
        ).execute()

    except HttpError as error:
        print('An error occurred: %s' % error)

    # Initialize variables for tracking the video with the most views
    max_views = 0
    link_of_max_views = ""
    title_of_max_views = ""
    image_of_max_views = ""

    # Loop through the retrieved video information to find the video with the most views
    for video_result in video_info['items']:
        video_id = video_result['id']
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        views = video_result['statistics']['viewCount']
        title = video_result['snippet']['title']
        thumbnail_url = video_result['snippet']['thumbnails']['high']['url']

        # Update the variables tracking the video with the most views if this video has more views
        if int(views) > int(max_views):
            max_views = views
            link_of_max_views = video_url
            title_of_max_views = title
            image_of_max_views = thumbnail_url

    # Create a dictionary with the information about the video with the most views
    data = {
        'youtubeLink': link_of_max_views,
        'title': title_of_max_views,
        'image': image_of_max_views
    }

    # Return the dictionary
    return data


def convert_fraction(string):
    if '½' in string:
        fraction = unicodedata.numeric('½')
        string = string.replace('½', str(fraction))
    elif '¼' in string:
        fraction = unicodedata.numeric('¼')
        string = string.replace('¼', str(fraction))
    return string


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


@api_view(['POST'])
def get_shopping_list_items(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = data['categoryID']

        # check if category ID is available
        if not category_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            shopping_list_category = ShoppingListCategory.objects.get(pk=category_id)
        except User.DoesNotExist:
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


@api_view(['POST'])
def check_availability(request):
    # get the list of names from the request
    data = json.loads(request.body)
    names = data['listOfItemsNames']
    # get the user's latitude and longitude from the request
    user_lat = float(data['userLat'])
    user_lon = float(data['userLon'])

    # get the list of items and markets
    items = Item.objects.filter(name__in=names)
    markets = Market.objects.all()

    # get the list of available items for each market
    market_items = []
    for market in markets:

        items_available = MarketItem.objects.filter(marketID=market, itemID__in=items)
        item_names_available = list(items_available.values_list('itemID__name', flat=True))

        available_items = [(name, name in item_names_available) for name in names]

        list_of_available_items = []
        for name in names:
            list_of_available_items.append(
                {
                    "itemName": name,
                    "isAvailable": name in item_names_available,
                }
            )

        item_ids = [item.itemID_id for item in items_available]
        num_available = len(item_ids)
        print(market.location)
        market_lat, market_lon = extract_lat_lon(market.location)

        # set connection with google api using api key
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
            'numAvailableItems': num_available,
            'availableItems': list_of_available_items,
            'distance': dist,
            'locationLink': market.location
        })

    # return the list of available items for each market as a JSON response
    return JsonResponse({'markets': market_items})


# these all functions/views not used for now


@api_view(['POST'])
def recipe_information_customized(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            website_url = data['website_url']
            scraper = scrape_me(website_url)
            data = {
                'title': scraper.title(),
                'time': scraper.total_time(),
                'picture_url': scraper.image(),
                'is_editor_choice': True,
                'ingredients': scraper.ingredients()
            }
            return JsonResponse(data)
        except:
            return HttpResponseBadRequest("Bad Request: Invalid request body")
    else:
        return HttpResponseBadRequest("Bad Request: Only POST requests are allowed")


@api_view(['POST'])
def recipe_information_origin(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            website_url = data['website_url']
            scraper = scrape_me(website_url)
            return Response(scraper.to_json(), status=status.HTTP_201_CREATED, )
        except:
            return HttpResponseBadRequest("Bad Request: Invalid request body")
    else:
        return HttpResponseBadRequest("Bad Request: Only POST requests are allowed")


@api_view(['POST'])
def ingredients_details(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ingredient = data['ingredient']
        quants = parser.parse(ingredient)
        ingredient_parce_name = parse(convert_fraction(ingredient))

        data = {
            'name': ingredient_parce_name['name'],
            'quantity': quants[0].value,
            'unit': quants[0].unit.name,
        }
        return JsonResponse(data)
    else:
        return HttpResponseBadRequest("Bad Request: Only GET requests are allowed")


@api_view(['GET'])
def send_name(request, name):
    if request.method == 'GET':
        return JsonResponse({"name": name})
    else:
        return HttpResponseBadRequest("Bad Request: Only GET requests are allowed")