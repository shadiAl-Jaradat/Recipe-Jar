from django.db import models
from django.utils import timezone

# ALL THESE CLASSES FOR WHISK APP #########################


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    phoneNumber = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True)
    weight = models.FloatField(null=True)
    height = models.FloatField(null=True)
    selectedShoppingList = models.CharField(max_length=150, null=True)

    def __str__(self):
        return self.firstName


class RecipeCategory(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipeCategories')
    orderID = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class Recipe(models.Model):
    id = models.UUIDField(primary_key=True)
    title = models.CharField(max_length=100)
    time = models.PositiveIntegerField(null=True, blank=True)
    pictureUrl = models.CharField(max_length=500, null=True, blank=True)
    videoUrl = models.CharField(max_length=500, null=True, blank=True)
    videoImage = models.CharField(max_length=500, null=True, blank=True)
    videoTitle = models.CharField(max_length=500, null=True, blank=True)
    videoDuration = models.CharField(max_length=500, null=True, blank=True)
    videoChannelName = models.CharField(max_length=500, null=True, blank=True)
    videoPostedDate = models.CharField(max_length=500, null=True, blank=True)
    isEditorChoice = models.BooleanField(default=False)
    category = models.ForeignKey(RecipeCategory, on_delete=models.CASCADE, related_name='recipes', null=True, blank=True)
    orderID = models.PositiveIntegerField()
    dateAdded = models.DateTimeField(default=timezone.now)
    userID = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipesAdded', null=True, blank=True)


    def __str__(self):
        return self.title


class Item(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=500)

    @property
    def __repr__(self):
        return self.name


class Unit(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=500)

    @property
    def __repr__(self):
        return self.name


class Ingredient(models.Model):
    id = models.UUIDField(primary_key=True)
    itemID = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemID')
    quantity = models.FloatField(null=True)
    unitID = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='UnitID', null=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    orderNumber = models.PositiveIntegerField()

    @property
    def __repr__(self):
        return self.id


class Step(models.Model):
    id = models.UUIDField(primary_key=True)
    description = models.CharField(max_length=500)
    orderID = models.PositiveIntegerField(null=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')

    @property
    def __repr__(self):
        return self.id


class ShoppingListCategory(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shoppingListCategories')
    icon = models.CharField(max_length=100)
    orderID = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class ShoppingListItem(models.Model):
    id = models.UUIDField(primary_key=True)
    itemID = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='item_id')
    categoryID = models.ForeignKey(ShoppingListCategory, on_delete=models.CASCADE, related_name='items')
    isCheck = models.BooleanField(default=False)
    orderNumber = models.PositiveIntegerField()

    @property
    def __repr__(self):
        return self.id


class Market(models.Model):
    id = models.UUIDField(primary_key=True)
    managerUserName = models.CharField(max_length=100)
    managerPassword = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    logo = models.CharField(max_length=1000)
    location = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class MarketItem(models.Model):
    id = models.UUIDField(primary_key=True)
    itemID = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='item')
    marketID = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='marketItems')

    @property
    def __repr__(self):
        return self.id

