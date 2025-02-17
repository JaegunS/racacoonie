# sets up the database for the application

import sqlite3

db = 'umdh.db'

conn = sqlite3.connect(db)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    hall TEXT
)
''')

cursor.execute('''
CREATE TABLE food (
    food_id INTEGER PRIMARY KEY,
    name TEXT
)
''')

cursor.execute('''
CREATE TABLE users_food (
    food_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (food_id) REFERENCES food(food_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
''')

conn.commit()