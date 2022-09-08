import json

# load secret information
with open('secret.json') as f:
	secret = json.load(f)

from basebot import bot

bot.run(secret['bot_token'])