import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext import tasks
import os
import asyncio
import sqlite3
from dotenv import load_dotenv
from umdh import get_menu, check_for_items, get_hall

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', intents=intents, help_command=commands.DefaultHelpCommand())

# Database name
db = 'umdh.db'

# Commands
@bot.command()
async def menu(ctx, hall: str = commands.param(default=None,description='Dining hall, using hyphens for multiple words'), menu_date: str = commands.param(default=None,description='Date in YYYY-MM-DD format')):
    '''
    Get menu for a dining hall
    If dining hall has multiple words, use dashes (e.g. east-quad)
    '''
    # if no hall is provided, use the user's default
    if hall is None:
        user_id = ctx.author.id
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute('SELECT hall FROM users WHERE user_id = ?', (user_id,))
        hall = c.fetchone()
        conn.close()
        if hall is None:
            await ctx.send('No dining hall provided.')
            return
        hall = hall[0]

    menu = get_menu(hall, menu_date)
    # format the menu
    formatted_menu = ''
    for meal, stations in menu.items():
        formatted_menu += f'**{meal.capitalize()}**\n'
        for station, items in stations.items():
            formatted_menu += f'**{station}**\n'
            formatted_menu += ', '.join(items) + '\n'
        formatted_menu += '\n'
    # split the message into multiple parts if it exceeds the limit
    if len(formatted_menu) > 2000:
        parts = [formatted_menu[i:i+2000] for i in range(0, len(formatted_menu), 2000)]
        for part in parts:
            await ctx.send(part)
    else:
        await ctx.send(formatted_menu)

@bot.command()
async def account(ctx):
    '''Create or view user account'''
    user_id = ctx.author.id
    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    
    if user is None:
        await ctx.send('What is your default dining hall?')
        try:
            hall_msg = await bot.wait_for('message', timeout=30, check=lambda m: m.author == ctx.author)
            hall = get_hall(hall_msg.content)
            if hall is None:
                await ctx.send('Invalid dining hall.')
                return
            c.execute('INSERT INTO users VALUES (?, ?)', (user_id, hall))
            conn.commit()
            await ctx.send('Account created!')
        except asyncio.TimeoutError:
            await ctx.send('Account creation timed out.')
            return

    c.execute('SELECT food.name FROM users_food JOIN food ON users_food.food_id = food.food_id WHERE users_food.user_id = ?', (user_id,))
    food_items = [item[0] for item in c.fetchall()]
    await ctx.send(f'Your tracked items: {", ".join(food_items) if food_items else "No items tracked"}')
    conn.close()

@bot.command()
async def add(ctx, *, food_item: str = commands.param(description='Food item to track')):
    '''Add food item to track'''
    user_id = ctx.author.id
    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    c.execute('SELECT food_id FROM food WHERE name = ?', (food_item,))
    result = c.fetchone()
    
    if not result:
        c.execute('INSERT INTO food (name) VALUES (?)', (food_item,))
        food_id = c.lastrowid
    else:
        food_id = result[0]
        
    c.execute('INSERT OR IGNORE INTO users_food VALUES (?, ?)', (food_id, user_id))
    conn.commit()
    conn.close()
    await ctx.send(f'Added {food_item} to tracked items!')

@bot.command()
async def remove(ctx, *, food_item: str = commands.param(description='Food item to remove')):
    '''Remove food item from tracked items'''
    user_id = ctx.author.id
    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    c.execute('SELECT food_id FROM food WHERE name = ?', (food_item,))
    result = c.fetchone()
    
    if not result:
        await ctx.send('Item not found.')
        return
    
    food_id = result[0]
    c.execute('DELETE FROM users_food WHERE user_id = ? AND food_id = ?', (user_id, food_id))
    conn.commit()
    conn.close()
    await ctx.send(f'Removed {food_item} from tracked items!')

@bot.command()
async def scrounge(ctx):
    '''
    Checks all dining halls for items in user's tracked list
    '''
    hall_items = check_for_items(ctx.author.id)
    # split the message into multiple parts if it exceeds the limit
    formatted_items = ''
    for hall, items in hall_items.items():
        formatted_items += f'**{hall}**\n'
        for item in items:
            formatted_items += f'{item["item"]} ({item["meal"]} - {item["station"]})\n'
        formatted_items += '\n'

    if not formatted_items:
        await ctx.send('No items found.')
        return

    if len(formatted_items) > 2000:
        parts = [formatted_items[i:i+2000] for i in range(0, len(formatted_items), 2000)]
        for part in parts:
            await ctx.send(part)
    else:
        await ctx.send(formatted_items)

# Bot events
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)