from dcmaid.basebot import Bot
from dcmaid.state import State

from load_secrets import secret
from load_db import db

state = State()
bot = Bot(db, state, debug_guilds = [secret['debug_server_id']])

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

# Install command groups here...
bot.load_extension('dcmaid.basecmd')

bot.run(secret['bot_token'])