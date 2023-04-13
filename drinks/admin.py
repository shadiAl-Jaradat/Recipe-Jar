from django.contrib import admin
from .models import User, Recipe, RecipeCategory, Ingredient, Step, Unit, Item, ShoppingListCategory, ShoppingListItem, \
    Market, MarketItem

admin.site.register(RecipeCategory)
admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(Step)
admin.site.register(Unit)
admin.site.register(Item)
admin.site.register(ShoppingListCategory)
admin.site.register(ShoppingListItem)
admin.site.register(Market)
admin.site.register(MarketItem)
admin.site.register(User)
