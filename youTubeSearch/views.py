import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

from .models import YoutubeVideo
from .serializer import VideoSerializer


@api_view(['GET'])
def get_video(request, text):
    search_url = 'https://www.googleapis.com/youtube/v3/search'

    params = {
        'part': 'snippet',
        'q': 'learn python',
        'key': settings.YOUTUBE_DATA_API_KEY
    }

    r = requests.get(search_url, params=params)
    print(r.text)
    return Response(text, status=status.HTTP_200_OK, )

