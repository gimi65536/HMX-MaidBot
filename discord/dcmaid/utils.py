import discord
from functools import wraps
from pathlib import PurePath
from typing import Any, Dict, List, Optional, Union
from .helper import set_help

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

def get_subcommand(group: discord.SlashCommandGroup, name: str) -> Optional[Union[discord.SlashCommand, discord.SlashCommandGroup]]:
	for cmd in group.subcommands:
		if cmd.name == name:
			return cmd
	return None

def walk_commands_and_groups(cmd):
	yield cmd
	if isinstance(cmd, discord.SlashCommandGroup):
		for subcmd in cmd.subcommands:
			yield from walk_commands_and_groups(subcmd)

async def send_as(ctx: Union[discord.ApplicationContext, discord.Interaction], webhook = None, *args, **kwargs):
	channel = ctx.channel
	if webhook is None:
		# Use bot
		await channel.send(*args, **kwargs)
	else:
		# Use webhook
		if isinstance(channel, discord.Thread):
			await webhook.send(*args, **kwargs, thread = channel)
		else:
			await webhook.send(*args, **kwargs)

def proxy(f_or_attr, /):
	if isinstance(f_or_attr, str):
		attr = f_or_attr
		def decorator(f):
			@wraps(f)
			def wrapper(self, *args, **kwargs):
				if hasattr(self, attr):
					self = getattr(self, attr)
				return f(self, *args, **kwargs)
			return wrapper
		return decorator
	else:
		f = f_or_attr
		@wraps(f)
		def wrapper(self, *args, **kwargs):
			if hasattr(self, '_proxy'):
				self = self._proxy
			return f(self, *args, **kwargs)
		return wrapper

def is_DM(channel):
	# So far, the DMChannel case won't be triggered at all.
	return isinstance(channel, (discord.PartialMessageable, discord.DMChannel))

def get_bot_name_in_ctx(ctx: discord.ApplicationContext) -> str:
	guild = ctx.guild
	if guild is None:
		return ctx.bot.user.display_name
	else:
		return guild.me.display_name

def int_to_emoji(i: int) -> str:
	s = str(i)
	l = []
	for c in s:
		match c:
			case '0':
				l.append(':zero:')
			case '1':
				l.append(':one:')
			case '2':
				l.append(':two:')
			case '3':
				l.append(':three:')
			case '4':
				l.append(':four:')
			case '5':
				l.append(':five:')
			case '6':
				l.append(':six:')
			case '7':
				l.append(':seven:')
			case '8':
				l.append(':eight:')
			case '9':
				l.append(':nine:')

	return ''.join(l)
