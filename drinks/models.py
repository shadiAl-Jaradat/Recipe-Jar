from django.db import models

# ALL THESE CLASSES FOR WHISK APP #########################


class User(models.Model):
    id = models.UUIDField(primary_key=True)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    phoneNumber = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True)
    dateOfBirth = models.DateTimeField(null=True)
    weight = models.FloatField(null=True)
    height = models.FloatField(null=True)

    def __str__(self):
        return self.firstName


class RecipeCategory(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipeCategories')
    orderID = models.PositiveIntegerField()

    def __str__(self):
        return self.id


class Recipe(models.Model):
    title = models.CharField(max_length=100)
    time = models.PositiveIntegerField(null=True)
    pictureUrl = models.CharField(max_length=500, null=True)
    videoUrl = models.CharField(max_length=500, null=True)
    is_editor_choice = models.BooleanField(default=False)
    category = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    orderID = models.PositiveIntegerField()

    def __str__(self):
        return self.id


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.FloatField(null=True)
    unit = models.CharField(max_length=100)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    orderNumber = models.PositiveIntegerField()

    @property
    def __str__(self):
        return self.id


class Step(models.Model):
    description = models.CharField(max_length=500)
    orderID = models.PositiveIntegerField(null=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')

    @property
    def __str__(self):
        return self.id


















