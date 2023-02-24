from django.urls import path
from . import views

urlpatterns = [
    path('getVideo/<str:text>', views.get_video)
]