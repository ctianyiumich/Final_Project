import requests
from bs4 import BeautifulSoup
import json
import sqlite3

conn = sqlite3.connect("C:\\jiaPiao\\Umich\\Si507\\Final Proj\\Recipes.sqlite")
cur = conn.cursor()
drop_recipes = '''
    DROP TABLE IF EXISTS "recipes"
'''
create_recipes = '''
    CREATE TABLE "recipes" (
	    "id"	INTEGER NOT NULL UNIQUE,
	    "url"	TEXT,
	    "title"	TEXT,
	    "ingredients"	TEXT,
	    PRIMARY KEY("id" AUTOINCREMENT)
    );
'''
cur.execute(drop_recipes)
cur.execute(create_recipes)
conn.commit()
insert_recipes ='''
    INSERT INTO recipes
    VALUES (NULL, ?, ?, ?)
'''
CACHE_json = "C:\\jiaPiao\\Umich\\Si507\\Final Proj\\index2page_CACHE.json"

BASE_URL="https://www.foodnetwork.com/recipes/recipes-a-z"

def load_cache():
    try:
        cache_file = open(CACHE_json, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache

def save_cache(cache):
    with open(CACHE_json, 'w', encoding='utf-8') as file_obj:
        json.dump(cache, file_obj, ensure_ascii=False, indent=2)

    """    cache_file = open(CACHE_json, 'w')
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()
    """

class Recipe:
    def __init__(self, url, name, ingredients):
        self.url = url
        self.name = name
        self.ingredients = ingredients

def get_recipes_url(CATALOG_URL):
    url2name_dict = {}
    recipes_response = requests.get(CATALOG_URL)
    recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")

    recipes_lis = recipes_soup.find_all('li', class_="m-PromoList__a-ListItem")

    for recipes_li in recipes_lis:
        recipes_tag = recipes_li.find('a')
        recipes_path = recipes_tag['href']
        url2name_dict['http:'+recipes_path] = recipes_tag.text.lower()
    return url2name_dict

def get_index():
    index2pages = {}
    recipes_catalog_response = requests.get(BASE_URL)
    recipes_catalog_soup = BeautifulSoup(recipes_catalog_response.text, 'html.parser')

    index_set = recipes_catalog_soup.find('ul', class_='o-IndexPagination__m-List')
    index_lis = index_set.find_all('li', recursive=False)

    for index_li in index_lis:
        index_a = index_li.find('a')
        index2pages[index_a.text.lower()]=None

    return index2pages

def get_page_number(INDEX):
    recipes_response = requests.get(BASE_URL+'/'+INDEX)
    recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")
    recipes_lis = recipes_soup.find_all('a', class_='o-Pagination__a-Button')
    return recipes_lis[-2].text

def index2page_combined():
    CACHE_dict = load_cache()
    if '123' in CACHE_dict.keys():
        return CACHE_dict
    else:
        index2page = get_index()
        for index in index2page.keys():
            index2page[index] = get_page_number(index)
        save_cache(index2page)
        return index2page

def get_ingredients_list(RECIPE_URL):
    ingredients_rawlist = []
    recipes_response = requests.get(RECIPE_URL)
    recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")
    #recipe_name = recipes_soup.find('span', class_='o-AssetTitle__a-HeadlineText').text
    recipe_ingredients = recipes_soup.find_all('span', class_='o-Ingredients__a-Ingredient--CheckboxLabel')
    for recipe_ingredient in recipe_ingredients[1:]:
        ingredients_rawlist.append(recipe_ingredient.text)
    return ingredients_rawlist

def url_maker(dict,index):
    url_list = []
    for i in range(int(dict[index])):
        url_list.append(BASE_URL+'/'+index+f'/p/{i+1}')
    return url_list

index2page_dict = index2page_combined()
url_list_123 = url_maker(index2page_dict, '123')
url2name_dict = get_recipes_url(url_list_123[0])
for recipe_url, recipe_name in url2name_dict.items():
    record = [recipe_url, recipe_name, str(get_ingredients_list(recipe_url))]
    cur.execute(insert_recipes, record)
    conn.commit()