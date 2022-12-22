from dcmaid.basebot import Bot
from dcmaid.state import State
from discord import Intents

from load_secrets import secret
from load_db import db

state = State()
intent = Intents.default()
intent.message_content = True
# intent.member = True # Enable it to reduce API call
if len(servers := secret['debug_server_id']) > 0:
	bot = Bot(db, state, intents = intent, debug_guilds = servers)
else:
	bot = Bot(db, state, intents = intent)

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

try:
	import uvloop  # type: ignore[import] # uvloop cannot be installed on Windows
except:
	pass
else:
	import asyncio
	asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Install command groups here...
bot.load_extension('dcmaid.basecmd')

for ext in secret['load_ext']:
	bot.load_extension(f'dcmaid.ext.{ext}')

bot.run(secret['bot_token'])