import bs4
import requests
import json
import sqlite3

url = 'https://dining.umich.edu/menus-locations/dining-halls/'
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

def check_for_items(user_id):
    '''
    input is list of items 
    [
        'hamburger',
        'pizza'
    ]
    returns a dictionary of halls and which items they have
    {
        'hall': {
            'item': 'item',
            'meal': 'meal',
            'station': 'station'
        }
    }
    '''
    # get user list
    conn = sqlite3.connect('umdh.db')
    c = conn.cursor()

    c.execute('SELECT food_id FROM users_food WHERE user_id = ?', (user_id,))
    result = c.fetchall()
    user_list = []
    for item in result:
        c.execute('SELECT name FROM food WHERE food_id = ?', (item[0],))
        user_list.append(c.fetchone()[0])
    
    hall_items = {}

    for hall in halls:
        menu = get_menu(hall)
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


    return hall_items


if __name__ == '__main__':
    print(json.dumps(check_for_items(365169403316142090), indent=4))