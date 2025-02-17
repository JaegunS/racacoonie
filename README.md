# Racacoonie
Racacoonie scrounges through the U-M dining hall menus on your behalf.
It was developed as a quick way to hunt down bulgogi fries. You can set up an account with your favorite items, and Racacoonie will tell you which dining halls have those items today.

If you just want to invite the bot to your server, click the link below:
https://discord.com/oauth2/authorize?client_id=1340933561980555305

The bot is currently hosted on my Macbook Air, so it may not be online 24/7.
If you want to self-host the bot, follow the instructions below.

## Usage
Use `?help` to get a list of commands.
To get started with Racacoonie, use `?account` to create an account.
From there, you can use `?add` to add items and `?remove` to remove items from your account.
These items are used when you `?scrounge` for a meal.
`?scrounge` will look through the dining hall menus for today and tell you which dining halls have items you like.
You can use `?menu <dining hall> <date>` to see the menu for a specific dining hall on a specific date. If no date is provided, it will default to today. If no dining hall is provided, it will default to the dining hall you have set in your account.

## Self-hosting
1. Clone the repository.
2. Install the required packages with `pip install -r requirements.txt`.
3. Create a `.env` file in the root directory with the following content:
```
DISCORD_TOKEN=<your bot token>
```
To get a bot token, go to the Discord Developer Portal and create a new application. Then, create a bot and copy the token.
4. Set up the SQLite database with `python setup.py`.
5. Run the bot with `python bot.py`.
