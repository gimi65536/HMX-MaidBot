import discord
from load_secrets import secret

from load_db import db
from load_maids import maids
from server_state import state

bot = discord.Bot(debug_guilds = [secret['debug_server_id']])

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

# Install command groups here...
from basebot import BasicCommands
bot.add_cog(BasicCommands(bot, db, maids, state))

bot.run(secret['bot_token'])