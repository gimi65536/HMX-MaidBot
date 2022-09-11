import discord
from dcmaid.state import State

from load_secrets import secret
from load_db import db
from load_maids import maids

state = State()
bot = discord.Bot(debug_guilds = [secret['debug_server_id']])

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

# Install command groups here...
from dcmaid.basebot import BasicCommands
bot.add_cog(BasicCommands(bot, db, maids, state))

bot.run(secret['bot_token'])