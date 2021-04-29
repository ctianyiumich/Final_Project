#########################################
##### Name: Tianyi Chi              #####
##### Uniqname: ctianyi             #####
#########################################
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import os
import plotly.graph_objs as go
from fractions import Fraction
from collections import Counter

BASE_URL="https://www.foodnetwork.com/recipes/recipes-a-z"
ingredients_row_list = []
ingredients_list = []
ingredients_list_cleaned = []
measure_words = ['bushel', 'bushel',
                'bunch', 'bunches',
                'box', 'boxes',
                'cup', 'cups',
                'clove', 'cloves',
                'dessertspoon', 'dessertspoons',
                'ounce', 'ounces', 'oz.',
                'gallon', 'gallons',
                'milliliter', 'milliliters',
                'liter', 'liters',
                'peck', 'pecks',
                'pint', 'pints',
                'quart', 'quarts',
                'can', 'cans',
                'tablespoon', 'tablespoons', 'tbsp',
                'teaspoon','teaspoons',
                'gram','grams',
                'kilogram', 'kilograms',
                'pound', 'pounds', 'lb.',
                'dozen', 'dosens',
                'to', 'plus', 'about'
                ]

#CACHE S&L
def load_cache(load_path):
    try:
        cache_file = open(load_path, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache

def save_cache(cache, save_path):
    with open(save_path, 'w', encoding='utf-8') as file_obj:
        json.dump(cache, file_obj, ensure_ascii=False, indent=2)

#每個首字母對應的頁數
def get_index_list():
    index_list = []
    recipes_catalog_response = requests.get(BASE_URL)
    recipes_catalog_soup = BeautifulSoup(recipes_catalog_response.text, 'html.parser')
    index_set = recipes_catalog_soup.find('ul', class_='o-IndexPagination__m-List')
    index_lis = index_set.find_all('li', recursive=False)

    for index_li in index_lis:
        index_a = index_li.find('a')
        index_list.append(index_a.text.lower())
    return index_list

def get_index2pagenum_dict(index_list):
    path = "index2page_dict.json"
    if load_cache(path) != {}:
        index2pagenum_dict = load_cache(path)
        return index2pagenum_dict
    else:
        index2pagenum_dict = {}
        for index in index_list:
            recipe_index_response = requests.get(BASE_URL+'/'+index)
            recipe_index_soup = BeautifulSoup(recipe_index_response.text, 'html.parser')
            index_pages = recipe_index_soup.find_all('a', class_='o-Pagination__a-Button')
            index2pagenum_dict[index] = index_pages[-2].text
        save_cache(index2pagenum_dict, path)
        return index2pagenum_dict

def get_rcpurl_list(catalog_url):
    rcpurl_list = []
    recipes_response = requests.get(catalog_url)
    recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")

    recipes_lis = recipes_soup.find_all('li', class_="m-PromoList__a-ListItem")

    for recipes_li in recipes_lis:
        recipes_tag = recipes_li.find('a')
        recipes_path = recipes_tag['href']
        rcpurl_list.append('http:'+recipes_path)
    return rcpurl_list
#fetch names
def get_name(rcp_url):
    try:
        recipes_response = requests.get(rcp_url)
        recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")
        name_tag = recipes_soup.find('span', class_="o-AssetTitle__a-HeadlineText")
        name = name_tag.text.lower()
        return name
    except:
        return None

#fetuch ingredients
def get_ingredients_rawlist(rcp_url):
    try:
        ingredients_rawlist = []
        recipes_response = requests.get(rcp_url)
        recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")
        recipe_ingredients = recipes_soup.find_all('span', class_='o-Ingredients__a-Ingredient--CheckboxLabel')
        for recipe_ingredient in recipe_ingredients[1:]:
            ingredients_rawlist.append(recipe_ingredient.text)
        return ingredients_rawlist
    except:
        return []

#fetch features
def get_features_rawlist(rcp_url):
    try:
        features_rawlist = []
        recipes_response = requests.get(rcp_url)
        recipes_soup = BeautifulSoup(recipes_response.text, "html.parser")
        recipe_features = recipes_soup.find('div', class_='o-Capsule__m-TagList m-TagList')
        recipe_features_as = recipe_features.find_all('a',class_='o-Capsule__a-Tag a-Tag')
        for recipe_feature in recipe_features_as:
            features_rawlist.append(recipe_feature.text)
        return features_rawlist
    except:
        return []

def add_ingredients_features2SQL(rcpurl_list):
    for rcpurl in rcpurl_list:
        name = get_name(rcpurl)
        ingredients_list = get_ingredients_rawlist(rcpurl)
        features_list = get_features_rawlist(rcpurl)
        record = [rcpurl, name, str(ingredients_list), str(features_list)]
        cur.execute(insert_recipes, record)
        conn.commit()

def remove_brackets(ingredient_str):
    try:
        ingredient_str_pop = ingredient_str.replace('(','*').replace(')','*').split('*').pop(1)
        return ingredient_str.replace(f"({ingredient_str_pop})", '')
    except:
        return ingredient_str

def remove_comma(ingredient_str):
    return ingredient_str.split(', ')[0]

def remove_measure_word(ingredient_str):
    if ingredient_str == None:
        return None
    else:
        for unit in measure_words:
            for word in ingredient_str.split(' '):
                if unit == word.lower():
                    ingredient_str = ingredient_str.replace(word, '')
    return ingredient_str

def remove_digits(ingredient_str):
    i=0
    ingredient_splited = ingredient_str.split(' ')
    for i in range(len(ingredient_splited)):
        try:
            ingredient_splited[i] = int(Fraction(ingredient_splited[i]))
        except:
            pass
    ingredient_str = str(ingredient_splited).replace('[','').replace(']','').replace("'", "").replace(", ", " ")
    for word in ingredient_str.split(' '):
        if word.isdigit():
            ingredient_str = ingredient_str.replace(word, '')
    return ingredient_str

def remove_dashword(ingredient_str):
    for word in ingredient_str.split(' '):
        if word.find('-') != -1:
            ingredient_str = ingredient_str.replace(word+' ', '')
    return ingredient_str

def remove_package(ingredient_str):
    packagelike = ['package', 'packages', 'packet', 'packets', 'piece', 'pieces']
    try:
        for word in packagelike:
            return ingredient_str.split(word)[1]
    except:
        return ingredient_str

def remove_single_s(ingredient_str):
    ingredient_str_spaced = " "+ingredient_str+" "
    try:
        return ingredient_str_spaced.replace(' s ', ' ').strip()
    except:
        return ingredient_str

def clean_ingredient_str(ingredient_str):
    ingredient_str = remove_brackets(ingredient_str)
    ingredient_str = remove_comma(ingredient_str)
    ingredient_str = remove_measure_word(ingredient_str)
    ingredient_str = remove_digits(ingredient_str)
    ingredient_str = remove_dashword(ingredient_str)
    ingredient_str = remove_package(ingredient_str)
    ingredient_str = remove_single_s(ingredient_str)
    return ingredient_str.strip().lower()

def create_plot(ingredients_list_cleaned, input_ingredients_digit):
    xvals = []
    yvals = []
    igd_c = Counter(ingredients_list_cleaned).most_common(int(input_ingredients_digit)+1)
    igd_c_dict = dict(igd_c)
    igd_c_dict[""]=0
    for ingredient in igd_c_dict.keys():
        xvals.append(ingredient)
        yvals.append(igd_c_dict[ingredient])
    #Ploting
    print('Got your request! Loading your bar chart...')
    bar_data = go.Bar(x=xvals[1:], y=yvals[1:])
    basic_layout = go.Layout(title=f"Most Commonly Used {int(input_ingredients_digit)} Ingredients of {input_title_str.lower()}")
    fig = go.Figure(data=bar_data, layout=basic_layout)
    fig.show()
    print('We got your bar chart! See the outcome in your browser.')

if __name__ == "__main__":
    #SQL
    SQLdatabase = "Recipes.sqlite"
    if os.path.exists(SQLdatabase) == False:
        print(f"Loading a new database. This may take a while...\n")
        conn = sqlite3.connect(SQLdatabase)
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
                "features"      TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
        '''
        cur.execute(drop_recipes)
        cur.execute(create_recipes)
        conn.commit()
        insert_recipes ='''
            INSERT INTO recipes
            VALUES (NULL, ?, ?, ?, ?)
        '''
        for index, page in get_index2pagenum_dict(get_index_list()).items():
            for p in range(int(page)):
                catalog_url = f"https://www.foodnetwork.com/recipes/recipes-a-z/{index}/p/{p}"
                rcp_url_list = get_rcpurl_list(catalog_url)
                add_ingredients_features2SQL(rcp_url_list)

    #User's input
    while True:
        greeting_input_str = input(f'''Hello!
                                        \nCheck the most popular ingredients by:
                                        \n1. a recipe title (e.g. Apple Pie, Beef Bourguignon, etc)
                                        \n2. a recipe feature (e.g. American, Gluten Free, etc.)
                                        \n3. a recipe title & feature
                                        \n4. Emmm... I need to check my gas stove right now. Bye! (exit)
                                        \nPlease press 1, 2, 3 or 4: ''')
        if greeting_input_str == '1':
            input_title_str = input(f'\nEnter a recipe title: ')
            while input_title_str.lower() != 'exit':
                ingredients_row_list = []
                ingredients_list = []
                ingredients_list_cleaned = []
                #Fetch data
                conn = sqlite3.connect(SQLdatabase)
                cur = conn.cursor()
                cur.execute(
                    f'SELECT ingredients FROM recipes WHERE title Like "%{input_title_str.lower()}%"'
                )
                for row in cur:
                    ingredients_row_list.append(row)
                if ingredients_row_list == []:
                    print("Sorry, we didn't find what you requested.")
                else:
                    #Data cleaning for ingredients
                    for ingredients in ingredients_row_list:
                        ingredients_list.extend(list(ingredients)[0].replace('[','').replace(']','').split("'"))
                    for item in ingredients_list:
                        ingredients_list_cleaned.append(clean_ingredient_str(item))

                    #Create frequency dictionary, data for ploting
                    input_ingredients_digit = input(f'How many ingredients would you like? \n')
                    while True:
                        try:
                            create_plot(ingredients_list_cleaned, input_ingredients_digit)
                            break
                        except:
                            input_ingredients_digit = input(f'We need a numerical number. Please try again. \n')
                input_title_str = input(f"\nTry another title or type 'exit' to go back: ")

        elif greeting_input_str == '2':
            input_title_str = input(f'\nEnter a recipe feature: ')
            while input_title_str.lower() != 'exit':
                ingredients_row_list = []
                ingredients_list = []
                ingredients_list_cleaned = []
                #Fetch data
                cur.execute(
                    f'SELECT ingredients FROM recipes WHERE features Like "%{input_title_str.lower()}%"'
                    )
                for row in cur:
                    ingredients_row_list.append(row)
                if ingredients_row_list == []:
                    print("Sorry, we didn't find what you requested.")
                else:
                    #Data cleaning for ingredients
                    for ingredients in ingredients_row_list:
                        ingredients_list.extend(list(ingredients)[0].replace('[','').replace(']','').split("'"))
                    for item in ingredients_list:
                        ingredients_list_cleaned.append(clean_ingredient_str(item))

                    #Create frequency dictionary, data for ploting
                    input_ingredients_digit = input(f'How many ingredients would you like? \n')
                    while True:
                        try:
                            create_plot(ingredients_list_cleaned, input_ingredients_digit)
                            break
                        except:
                            input_ingredients_digit = input(f'We need a numerical number. Please try again. \n')
                input_title_str = input(f"\nTry another feature or type 'exit' to go back: ")
        elif greeting_input_str == '3':
            input_title_str = input(f'\nEnter a recipe title first: ')
            input_f_str = input(f'\nAnd a recipe feature: ')
            while input_title_str.lower() != 'exit':
                ingredients_row_list = []
                ingredients_list = []
                ingredients_list_cleaned = []
                #Fetch data
                cur.execute(
                    f'SELECT ingredients FROM recipes WHERE title Like "%{input_title_str.lower()}%"AND features Like "%{input_f_str.lower()}%"'
                    )
                for row in cur:
                    ingredients_row_list.append(row)
                if ingredients_row_list == []:
                    print("Sorry, we didn't find what you requested.")
                else:
                    #Data cleaning for ingredients
                    for ingredients in ingredients_row_list:
                        ingredients_list.extend(list(ingredients)[0].replace('[','').replace(']','').split("'"))
                    for item in ingredients_list:
                        ingredients_list_cleaned.append(clean_ingredient_str(item))

                    #Create frequency dictionary, data for ploting
                    input_ingredients_digit = input(f'How many ingredients would you like? \n')
                    while True:
                        try:
                            create_plot(ingredients_list_cleaned, input_ingredients_digit)
                            break
                        except:
                            input_ingredients_digit = input(f'We need a numerical number. Please try again. \n')
                input_title_str = input(f"\nTry another title or type 'exit' to go back: ")
                if input_title_str.lower() != 'exit':
                    input_f_str = input(f'\nAnd another recipe feature: ')
                else:
                    break

        elif greeting_input_str == '4':
            print('Have a great day!')
            conn.close()
            break
        else:
            print(f'Error: Invalid input.\n')
