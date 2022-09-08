import discord

bot = discord.Bot()

@bot.event
async def on_ready():
	print(f'Successfully logged in as {bot.user}.')

__all__ = ['bot']