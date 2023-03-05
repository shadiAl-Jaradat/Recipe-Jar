from django.contrib import admin
from .models import User, Recipe, RecipeCategory, Ingredient, Step, Unit, Item

admin.site.register(User)
admin.site.register(RecipeCategory)
admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(Step)
admin.site.register(Unit)
admin.site.register(Item)
