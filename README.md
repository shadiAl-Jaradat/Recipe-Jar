# Recipe Jar - Backend 

# Overview

This project is the backend of the Recipe Jar system. It provides a set of RESTful APIs that are used by the Recipe Jar iOS app to search for recipes and retrieve detailed information about them. The APIs are designed to be easy to use and provide a seamless user experience.

FrontEnd - [@RecipeJar IOS App](https://github.com/othmansh0/Recipe-Jar)

# APIs Used : 

●  [OpenAI API](https://openai.com/blog/openai-api) : Used to scrape recipe information from text and convert it to JSON format.
 
●  [YouTube API](https://developers.google.com/youtube) : Used to retrieve the most viewed recipe videos from YouTube.

●  [Google Maps Platform API](https://mapsplatform.google.com) : Used to retrieve location data and calculate the distance between two points.


# Packages Used :

●  [recipe_scrapers](https://github.com/hhursev/recipe-scrapers) : A Python package used to scrape recipe data from various websites.

●  [quantulum3](https://github.com/nielstron/quantulum3) : Python library for information extraction of quantities, measurements and their units from          unstructured text. I used to return the quantity and unit for each in ingredient.

●  [pandas](https://pandas.pydata.org/docs/getting_started/overview.html#:~:text=pandas%20is%20a%20Python%20package,world%20data%20analysis%20in%20Python.) : A Python package used to read Excel files and manipulate data.
