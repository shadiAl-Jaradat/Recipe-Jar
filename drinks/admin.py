from django.contrib import admin
from .models import User, Recipe, RecipeCategory, Ingredient, Step

admin.site.register(User)
admin.site.register(RecipeCategory)
admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(Step)
