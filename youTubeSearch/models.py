from django.db import models


# Create your models here.

class YoutubeVideo(models.Model):
    text = models.CharField(max_length=200)
    videoUrl = models.CharField(max_length=500)

    def __str__(self):
        return self.videoUrl
