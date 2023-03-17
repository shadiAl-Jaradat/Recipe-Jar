import unicodedata
from django.db.models import Window
from django.db.models import F
from django.db.models.functions import RowNumber
from rest_framework.generics import get_object_or_404
from .serializer import IngredientSerializer, RecipeSerializer, RecipeCategorySerializer, StepSerializer, \
    UserSerializer, ShoppingListCategorySerializer, ShoppingListItemSerializer
from .models import User, Recipe, Ingredient, Step, RecipeCategory, Unit, Item, ShoppingListCategory, ShoppingListItem
from pytube import YouTube
from googleapiclient.discovery import build
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, serializers
import json
from django.http import JsonResponse, HttpResponseBadRequest
from recipe_scrapers import scrape_me
from uuid import UUID, uuid4
from quantulum3 import parser
from ingredient_parser.en import parse
from django.shortcuts import render
from typing import TypeVar

def home(request):
    context = {'title': 'Whisk App'}
    return render(request, 'whiskTemplates/home.html', context)


@api_view(['POST'])
def create_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = User(
            id=UUID(data['userID']),
            firstName=data['firstName'],
            lastName=data['lastName'],
            phoneNumber=data['phoneNumber'],
            age=data['age'],
            dateOfBirth=data['dateOfBirth'],
            weight=data['weight'],
            height=data['height'],
        )
        user.save()
        serialized_user = UserSerializer(user)
        return JsonResponse(serialized_user.data, status=status.HTTP_200_OK)


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
        ).filter(category=category).order_by('orderID').exclude(orderID__isnull=True).values('id', 'videoUrl', 'videoTitle', 'videoImage', 'title', 'time', 'pictureUrl', 'is_editor_choice', 'orderIDNEW')
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
def get_recipe_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        recipe_id = UUID(data['RecipeID'])
        recipe = Recipe.objects.get(pk=recipe_id)

        ingredients = Ingredient.objects.filter(recipe=recipe)
        serialized_ingredients = IngredientSerializer(ingredients, many=True)

        steps = Step.objects.filter(recipe=recipe)
        serialized_steps = StepSerializer(steps, many=True)

        # list_ingredients = serialized_ingredients.data
        list_ingredients = []

        for ingredient in serialized_ingredients.data:

            item_id = ingredient['itemID']
            item_from_db = Item.objects.get(id=item_id)
            # serialized_item = ItemSerializer(item_from_db, many=True)

            quantity = ingredient['quantity']

            unit_name = ""
            if ingredient['unitID']:
                unit_id = ingredient['unitID']
                unit_from_db = Unit.objects.get(id=unit_id)
                unit_name = unit_from_db.name
            else:
                unit_name = None

            # serialized_unit = UnitSerializer(unit_from_db, many=True)

            order_id = ingredient['orderNumber']

            list_ingredients.append(
                {
                    'name': item_from_db.name,
                    'quantity': quantity,
                    'unit': unit_name,
                    'orderNumber': order_id
                }
            )

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

        data = {
            'ingredients': list_ingredients,
            'steps': list_steps,
        }

        return Response(data, status=status.HTTP_200_OK)
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
                unit = ""

            ingredient_parce_name = parse(convert_fraction(ingredient))

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
    api_key = 'AIzaSyC1xBiPhp9D2UIh4dIeGjlex90s3BZ5me4'
    youtube = build('youtube', 'v3', developerKey=api_key)
    search_response = youtube.search().list(
        q=query + ' recipe',
        type='video',
        part='id,snippet',
        maxResults=30
    ).execute()
    max_views = 0
    link_of_max_views = ""
    title_of_max_views = ""
    image_of_max_views = ""
    for search_result in search_response.get('items', []):
        video_id = search_result['id']['videoId']
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        video = YouTube(video_url)
        if video.views > max_views:
            max_views = video.views
            link_of_max_views = video_url
            title_of_max_views = video.title
            image_of_max_views = video.thumbnail_url
        else:
            break
    data = {
        'youtubeLink': link_of_max_views,
        'title': title_of_max_views,
        'image': image_of_max_views
    }
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
        user_id = data['userID']
        temp_user = User.objects.get(pk=user_id)
        shopping_list_categories = ShoppingListCategory.objects.filter(user=temp_user).order_by('orderID')
        order_id = len(shopping_list_categories) + 1

        temp_category = ShoppingListCategory(
            id=category_uuid,
            name=name,
            orderID=order_id,
            user=temp_user
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
        if not user_id:
            return Response({"error": "userID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        categories = ShoppingListCategory.objects.annotate(
            orderIDNEW=Window(
                expression=RowNumber(),
                order_by=F('orderID')
            )
        ).filter(user=user).order_by('orderID')
        list_of_categories = []
        for category in categories:
            # TODO: return items of category with each of it
            # list_of_items = ShoppingListItem.objects.filter(category=category['id'])
            list_of_categories.append(
                {
                    'id': category['id'],
                    'name': category['name'],
                    'orderID': category['orderIDNEW'],
                }
            )
        return Response(list_of_categories, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


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
        shopping_list_item.save()
        serialized_shopping_list_item = ShoppingListItemSerializer(shopping_list_item)
        return JsonResponse(serialized_shopping_list_item.data, status=status.HTTP_200_OK)
    else:
        JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def toggle_item_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data['itemID']
        item = ShoppingListItem.objects.get(pk=item_id)
        if item.isCheck:
            item.isCheck = False
        else:
            item.isCheck = True
        item.save()
        new_status = str(item.isCheck)
        return JsonResponse({'message': f'item status = {new_status}'}, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message': 'this API is POST API '}, status=status.HTTP_400_BAD_REQUEST)

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
