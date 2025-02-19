import discord
from discord.ext import commands
import os
import asyncio
import sqlite3
from dotenv import load_dotenv
from umdh import get_menu, get_cached_menu, check_for_items_cached, get_menu, get_hall, cache_check, add_food, remove_food, get_user_food, format_hall_items, format_menu, update_cache
from datetime import datetime, timezone, timedelta

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
            await ctx.send('You haven\'t set a default dining hall. Please use the `account` command to set one.')
            return
        hall = hall[0]

    cache_check()

    # if the date is None, use cache
    if menu_date is None:
        menu = get_cached_menu(hall)
    else:
        if menu_date == 'tomorrow':
            menu_date = datetime.now(timezone.utc).date() + timedelta(days=1)
            # needs to be in YYYY-MM-DD format
            menu_date = menu_date.strftime('%Y-%m-%d')
        menu = get_menu(hall, menu_date)

    formatted_menu = format_menu(menu)

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
    
    # if user doesn't exist, guide through account creation
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
            return
        except asyncio.TimeoutError:
            await ctx.send('Account creation timed out.')
            return

    food_items = get_user_food(user_id)
    await ctx.send(f'Your tracked items: {", ".join(food_items) if food_items else "No items tracked"}')
    await ctx.send(f'Your default dining hall: {user[1]}')
    conn.close()

@bot.command()
async def add(ctx, *, food_item: str = commands.param(description='Food item to track')):
    '''Add food item to track'''
    if not food_item:
        await ctx.send('No food item provided.')
        return
    
    add_food(ctx.author.id, food_item)

    await ctx.send(f'Added {food_item} to tracked items!')

@bot.command()
async def remove(ctx, *, food_item: str = commands.param(description='Food item to remove')):
    '''Remove food item from tracked items'''
    if not food_item:
        await ctx.send('No food item provided.')
        return
    
    remove_food(ctx.author.id, food_item)

    await ctx.send(f'Removed {food_item} from tracked items!')

@bot.command()
async def scrounge(ctx):
    '''
    Checks all dining halls for items in user's tracked list
    '''
    cache_check()
    hall_items = check_for_items_cached(ctx.author.id)
    # split the message into multiple parts if it exceeds the limit
    formatted_items = format_hall_items(hall_items)

    if not formatted_items:
        await ctx.send('No items found.')
        return

    if len(formatted_items) > 2000:
        parts = [formatted_items[i:i+2000] for i in range(0, len(formatted_items), 2000)]
        for part in parts:
            await ctx.send(part)
    else:
        await ctx.send(formatted_items)

@bot.command()
async def update(ctx):
    '''
    Updates the cache
    '''
    update_cache()
    await ctx.send('Cache updated!')


# region Bot events
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)
# endregion
