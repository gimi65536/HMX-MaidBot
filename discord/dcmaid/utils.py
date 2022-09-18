import discord
from pathlib import PurePath
from typing import Any, Dict, List, Optional, Union

# When creating commands, 'guild_only' does the same thing as what this fundtion does.
# But for convenience, we preserve this function.
def check_server_text_channel(ctx: discord.ApplicationContext):
	if isinstance(ctx.channel, discord.TextChannel):
		return True
	raise discord.CheckFailure('This command is only for text channels in servers.')

# Retrieve maid names from the cog within the ctx.
# If the cog does not have "maids" dict, then an empty list is returned.
def autocomplete_get_maid_names(ctx: discord.AutocompleteContext) -> List[str]:
	cog = ctx.cog
	try:
		maids: Dict[str, Any] = cog.maids
	except:
		return []

	return list(maids.keys())

# Given a messageable chat room in a guild, returns the parent channel if the chat room
# is a thread, otherwise returns the argument itself.
def get_guild_channel(ch: Union[discord.abc.GuildChannel, discord.Thread]):
	if isinstance(ch, discord.Thread):
		return ch.parent

	return ch

# A simple function to send an embed to indicate an error.
# The embed contains one field only.
async def send_error_embed(ctx: Union[discord.ApplicationContext, discord.Interaction],
		name, value, title = discord.Embed.Empty, description = discord.Embed.Empty, **kwargs):
	embed = discord.Embed(color = discord.Color.red(), title = title, description = description)
	embed.add_field(
		name = name,
		value = value
	)
	if isinstance(ctx, discord.ApplicationContext):
		await ctx.send_response(embed = embed, **kwargs)
	else:
		await ctx.response.send_message(embed = embed, **kwargs)

def trim(string: Optional[str]):
	if string is not None:
		return string.strip()
	return None

# This function removes the "thinking" mode without sending anything from the interaction.
async def remove_thinking(ctx: Union[discord.ApplicationContext, discord.Interaction]):
	if isinstance(ctx, discord.ApplicationContext):
		await ctx.defer()
		await ctx.delete()
	else:
		await ctx.response.defer()
		await ctx.delete_original_message()

def add_suffix(path: PurePath, suffix: str):
	return path.with_suffix(path.suffix + suffix)
