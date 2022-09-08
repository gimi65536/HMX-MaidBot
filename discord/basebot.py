import discord
from debug_utils import gen_gids
from utils import check_server_text_channel

bot = discord.Bot()

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

# Basic commands

kwargs_for_text_channel = {'checks': [check_server_text_channel], 'guild_ids': gen_gids()}

async def _initialize__base(ctx):
	channel_id = ctx.channel_id
	...

@bot.slash_command(**kwargs_for_text_channel)
async def initialize(ctx):
	await _initialize__base(ctx)

@bot.slash_command(**kwargs_for_text_channel)
async def introduce(ctx):
	await _initialize__base(ctx)
	...

__all__ = ['bot']