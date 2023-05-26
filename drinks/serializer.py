from rest_framework import serializers
from .models import User, Recipe, RecipeCategory, Ingredient, Step, ShoppingListCategory, ShoppingListItem, Market, \
    MarketItem


# ALL THESE Serializers FOR WHISK APP #########################

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'firstName', 'lastName', 'phoneNumber', 'age', 'weight', 'height')
        extra_kwargs = {
            'firstName': {'required': False},
            'phoneNumber': {'required': False},
            'lastName': {'required': False},
        }


class RecipeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeCategory
        fields = '__all__'


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = '__all__'


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class ShoppingListCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListCategory
        fields = "__all__"


class ShoppingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = "__all__"


class MarketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = "__all__"


class MarketItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = MarketItem
        fields = "__all__"
