import bs4
import requests
import sqlite3
from datetime import datetime, timezone

url = 'https://dining.umich.edu/menus-locations/dining-halls/'

# region Hall functions
halls = [
    'bursley',
    'east-quad',
    'markley',
    'mosher-jordan',
    'north-quad',
    'south-quad',
    'twigs-at-oxford'
]

hall_aliases = {
    'bursley': ['bursley', 'burs'],
    'east-quad': ['east-quad', 'east quad', 'east', 'eq'],
    'markley': ['markley', 'mark'],
    'mosher-jordan': ['mosher-jordan', 'mosher jordan', 'mj', 'mojo'],
    'north-quad': ['north-quad', 'north quad', 'north', 'nq'],
    'south-quad': ['south-quad', 'south quad', 'south', 'sq'],
    'twigs-at-oxford': ['twigs-at-oxford', 'twigs at oxford', 'twigs', 'oxford', 'twinner']
}

def get_hall(hall):
    for key in hall_aliases:
        if hall.lower() in hall_aliases[key]:
            return key
    if hall.lower() in halls:
        return hall
    return None
# endregion

def get_user_food(user_id):
    '''
    returns a list of the user's food items
    '''
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    c.execute('SELECT food_id FROM users_food WHERE user_id = ?', (user_id,))
    result = c.fetchall()
    user_list = []
    for item in result:
        c.execute('SELECT name FROM food WHERE food_id = ?', (item[0],))
        user_list.append(c.fetchone()[0])

    conn.close()

    return user_list

def get_menu(hall, menu_date=None):
    '''
    returns a dict of the menu for the given dining hall
    {
        'breakfast': {
            'station': {
                'item': 'description'
            }
        },
        ...
    }
    '''
    hall = get_hall(hall)

    r = requests.get(url + hall + '/' + ('' if menu_date is None else '?menuDate=' + menu_date))
    soup = bs4.BeautifulSoup(r.text, 'html.parser')

    menu = {}

    # meals downstream of 'mdining-items' id
    meals = soup.find(id='mdining-items')

    # div class 'courses' is under an <h3> with the meal name
    for meal in meals.find_all('h3'):
        meal_name = meal.text.strip()
        menu[meal_name] = {}

        for station in meal.find_next('div').find('ul').find_all('li'):
            # each li element has a station name (h4)
            # and items (ul)
            station_name_tag = station.find('h4')
            if station_name_tag:
                station_name = station_name_tag.text.strip()
                menu[meal_name][station_name] = []

                for item in station.find('ul').find_all('li'):
                    # each li element has a div with the item name
                    # class = 'item-name'
                    item_name = item.find('div', class_='item-name')
                    if item_name:
                        item_name = item_name.text.strip()
                        menu[meal_name][station_name].append(item_name)

    return menu

def get_cached_menu(hall):
    '''
    returns the menu for the given dining hall from the cache
    '''
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    c.execute('SELECT * FROM menu WHERE hall = ?', (hall,))
    result = c.fetchall()

    menu = {}

    for item in result:
        hall = item[0]
        meal = item[1]
        station = item[2]
        item = item[3]

        if meal not in menu:
            menu[meal] = {}
        if station not in menu[meal]:
            menu[meal][station] = []
        
        menu[meal][station].append(item)

    conn.close()

    return menu

def check_for_items_cached(user_id):
    '''
    checks for items in the user's list using the cached menu
    '''
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    user_list = get_user_food(user_id)

    hall_items = {}

    for hall in halls:
        menu = get_cached_menu(hall)
        for meal in menu:
            for station in menu[meal]:
                for item in menu[meal][station]:
                    for items in user_list:
                        if items.lower() in item.lower():
                            if hall not in hall_items:
                                hall_items[hall] = []
                            hall_items[hall].append({
                                'item': item,
                                'meal': meal,
                                'station': station
                            })
    
    conn.close()

    return hall_items

def update_cache():
    '''
    updates the menu cache
    '''
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    # clear the table
    c.execute('DELETE FROM menu')

    for hall in halls:
        menu = get_menu(hall)
        for meal in menu:
            for station in menu[meal]:
                for item in menu[meal][station]:
                    c.execute('INSERT INTO menu VALUES (?, ?, ?, ?)', (hall, meal, station, item))

    conn.commit()
    conn.close()

    with open("last_scrape.txt", "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())

def cache_check():
    '''
    Checks if the cache needs to be updated and updates it if necessary
    '''
    with open("last_scrape.txt", "r") as f:
        last_scrape = f.read()
    last_scrape = datetime.fromisoformat(last_scrape)
    if datetime.now(timezone.utc).date() > last_scrape.date() and datetime.now(timezone.utc).hour >= 2:
        update_cache()
        with open("last_scrape.txt", "w") as f:
            f.write(datetime.now(timezone.utc).isoformat())

def add_food(user_id, food):
    '''
    Adds a food item to the user's list
    '''
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    c.execute('SELECT food_id FROM food WHERE name = ?', (food,))
    result = c.fetchone()

    if not result:
        c.execute('INSERT INTO food (name) VALUES (?)', (food,))
        food_id = c.lastrowid
    else:
        food_id = result[0]
    
    c.execute('INSERT OR IGNORE INTO users_food VALUES (?, ?)', (food_id, user_id))
    conn.commit()
    conn.close()

def remove_food(user_id, food):
    '''
    Removes a food item from the user's list
    '''
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    c.execute('SELECT food_id FROM food WHERE name = ?', (food,))
    result = c.fetchone()

    if not result:
        return
    
    food_id = result[0]
    c.execute('DELETE FROM users_food WHERE user_id = ? AND food_id = ?', (user_id, food_id))
    conn.commit()
    conn.close()

def format_hall_items(hall_items):
    '''
    Formats the hall items into a string
    '''
    formatted = ''
    for hall in hall_items:
        formatted += f'**{hall}**\n'
        for item in hall_items[hall]:
            formatted += f'**{item["meal"]}** at **{item["station"]}**\n'
            formatted += item["item"] + '\n'
        formatted += '\n'
    return formatted

def format_menu(menu):
    '''
    Formats the menu into a string
    '''
    formatted_menu = ''
    for meal, stations in menu.items():
        formatted_menu += f'**{meal.capitalize()}**\n'
        for station, items in stations.items():
            formatted_menu += f'**{station}**\n'
            formatted_menu += ', '.join(items) + '\n'
        formatted_menu += '\n'
    return formatted_menu