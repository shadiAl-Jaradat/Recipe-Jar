from rest_framework import serializers
from .models import YoutubeVideo


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = YoutubeVideo
        fields = ['text', 'videoUrl']
