import unicodedata

from .serializer import IngredientSerializer, RecipeSerializer
from .models import User, Recipe, Ingredient, Step, RecipeCategory
from pytube import YouTube
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from django.http import JsonResponse, HttpResponseBadRequest
from recipe_scrapers import scrape_me
import uuid
from quantulum3 import parser
from ingredient_parser.en import parse
import re
import spacy
from py4j.java_gateway import JavaGateway


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


@api_view(['POST'])
def create_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_uuid = uuid.uuid4()
        user = User(
            id=user_uuid,
            firstName=data['firstName'],
            lastName=data['lastName'],
            phoneNumber=data['phoneNumber'],
            age=data['age'],
            dateOfBirth=data['dateOfBirth'],
            weight=data['weight'],
            height=data['height'],
        )
        user.save()
        return JsonResponse({'message': 'User created successfully'})


@api_view(['POST'])
def save_recipe(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = data.get('category_id')
        recipe_data = data.get('recipe')
        ingredients_data = data.get('ingredients')
        steps_data = data.get('steps')

        category = RecipeCategory.objects.get(id=category_id)
        recipe = Recipe.objects.create(
            title=recipe_data.get('title'),
            time=recipe_data.get('time'),
            pictureUrl=recipe_data.get('pictureUrl'),
            videoUrl=recipe_data.get('videoUrl'),
            is_editor_choice=recipe_data.get('is_editor_choice'),
            category=category,
            orderID=recipe_data.get('orderID')
        )
        recipe.save()

        for ingredient in ingredients_data:
            Ingredient.objects.create(
                name=ingredient.get('name'),
                quantity=ingredient.get('quantity'),
                unit=ingredient.get('unit'),
                recipe=recipe,
                orderNumber=ingredient.get('orderNumber')
            ).save()

        for step in steps_data:
            Step.objects.create(
                description=step.get('description'),
                orderID=step.get('orderID'),
                recipe=recipe
            ).save()

        return JsonResponse({'message': 'Recipe created successfully'})
    else:
        return JsonResponse({'message': 'Bad request'}, status=400)


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
def recipe_information_customized_last_version(request):
    try:
        data = json.loads(request.body)
        website_url = data['websiteUrl']
        scraper = scrape_me(website_url)

        ingredients = []

        steps = []

        for ingredient in scraper.ingredients():
            quants = parser.parse(ingredient)
            if quants.__len__() == 0:
                quantity = ""
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
        return Response(recipe_data, status=status.HTTP_201_CREATED, )
    except:
        return HttpResponseBadRequest("Scraping not supported for this URL")


# @api_view(['POST'])
# def recipe_information_customized_two(request):
#     if request.method == 'POST':
#         data = json.loads(request.body)
#         website_url = data['website_url']
#         scraper = scrape_me(website_url)
#         temp_recipe = Recipe.objects.create(
#             name=scraper.title(),
#             time=scraper.total_time(),
#             picture_url=scraper.image(),
#             scale=3,
#             is_editor_choice=False
#         )
#
#         list_ingredient = scraper.ingredients()
#         for ingredient in list_ingredient:
#             temp_ingredient = Ingredient.objects.create(
#                 name=ingredient,
#                 recipe=temp_recipe,
#             )
#
#         ingredients = Ingredient.objects.filter(recipe=temp_recipe)
#         ingredients_data = []
#         for ingredient in ingredients:
#             ingredients_data.append({
#                 'name': ingredient.name,
#             })
#
#         data = {
#             'name': temp_recipe.name,
#             'time': temp_recipe.time,
#             'picture_url': temp_recipe.picture_url,
#             'scale': temp_recipe.scale,
#             'is_editor_choice': temp_recipe.is_editor_choice,
#             'ingredients': ingredients_data
#         }
#         return JsonResponse(data)
#     else:
#         return HttpResponseBadRequest("Bad Request: Only POST requests are allowed")


@api_view(['POST'])
def recipe_information_origin(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            website_url = data['website_url']
            scraper = scrape_me(website_url)
            return Response(scraper.to_json(), status=status.HTTP_201_CREATED, )
            # return Response(scraper.to_json(), status=status.HTTP_201_CREATED,)
        except:
            return HttpResponseBadRequest("Bad Request: Invalid request body")
    else:
        return HttpResponseBadRequest("Bad Request: Only POST requests are allowed")
