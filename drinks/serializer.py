from rest_framework import serializers
from .models import User, Recipe, RecipeCategory, Ingredient, Step


# ALL THESE Serializers FOR WHISK APP #########################

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'time', 'picture_url', 'is_editor_choice']


class RecipeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeCategory
        fields = ['id', 'name']


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'time', 'picture_url', 'is_editor_choice']


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'quantity', 'unit']


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'description', 'orderID']
