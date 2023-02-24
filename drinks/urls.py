"""drinks URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drinks import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('createUser/', views.create_user, name="firstName=string, lastName=string, phoneNumber=string, age=int, dateOfBirth=DateTime, weight=float, height=float,"),
    path('sendAndGetMyName/<str:name>/', views.send_name,),
    path('whiskApp/getOriginRecipeInfo/', views.recipe_information_origin, name='website_url'),
    path('whiskApp/getCustomizedRecipeInfo/', views.recipe_information_customized, name="website_url"),
    path('whiskApp/webExtension/getRecipeInformation/', views.recipe_information_customized_last_version, name="website_url"),
    path('YoutubeVideo/', views.get_video),
    path('GetIngredientsDetails/', views.ingredients_details)
]
