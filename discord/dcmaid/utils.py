import discord
from asyncio import get_running_loop
from decouple import config, Csv  # type: ignore[import]
from functools import wraps
from typing import Any, Optional, TYPE_CHECKING
from .typing import QuasiContext

if TYPE_CHECKING:
	from .typing import Channelable

EmptyCharacter = '\u200b'

# When creating commands, 'guild_only' does the same thing as what this fundtion does.
# But for convenience, we preserve this function.
def check_server_text_channel(ctx: QuasiContext):
	if isinstance(ctx.channel, discord.TextChannel):  # type: ignore[arg-type]
		return True
	raise discord.CheckFailure('This command is only for text channels in servers.')

# Retrieve maid names from the cog within the ctx.
# If the cog does not have "maids" dict, then an empty list is returned.
def autocomplete_get_maid_names(ctx: discord.AutocompleteContext) -> list[str]:
	cog = ctx.cog
	if cog is None or not hasattr(cog, 'maids'):
		return []

	maids: dict[str, Any] = cog.maids

	return list(maids.keys())

# Given a messageable chat room in a guild, returns the parent channel if the chat room
# is a thread, otherwise returns the argument itself.
def get_guild_channel(ch: discord.abc.GuildChannel | discord.Thread):
	if isinstance(ch, discord.Thread):
		if ch.parent is None:
			return get_running_loop().run_until_complete(discord.utils.get_or_fetch(ch.guild, 'channel', ch.parent_id))
		return ch.parent

	return ch

# A simple function to send an embed to indicate an error.
# The embed contains one field only.
# This method automatically detect whether the response is done or not to use followup.
# ApplicationContext: send_response()
# Interaction: response.send_message()
# Webhook (this is followup): send()
# Message: reply()
async def send_error_embed(ctx: QuasiContext | discord.Webhook | discord.Message, name, value, title = discord.Embed.Empty, description = discord.Embed.Empty, **kwargs):
	embed = discord.Embed(color = discord.Color.red(), title = title, description = description)
	embed.add_field(
		name = name,
		value = value
	)
	if isinstance(ctx, discord.ApplicationContext):
		if ctx.response.is_done():
			await ctx.send_followup(embed = embed, **kwargs)
		else:
			await ctx.send_response(embed = embed, **kwargs)
	elif isinstance(ctx, discord.Interaction):
		if ctx.response.is_done():
			await ctx.followup.send(embed = embed, **kwargs)
		else:
			await ctx.response.send_message(embed = embed, **kwargs)
	elif isinstance(ctx, discord.Webhook):
		await ctx.send(embed = embed, **kwargs)
	else:
		await ctx.reply(embed = embed, **kwargs)

def trim(string: Optional[str]):
	if string is not None:
		return string.strip()
	return None

# This function removes the "thinking" mode without sending anything from the interaction.
async def remove_thinking(ctx: QuasiContext):
	try:
		if isinstance(ctx, discord.ApplicationContext):
			await ctx.defer()
			await ctx.delete()
		else:
			await ctx.response.defer()
			await ctx.delete_original_response()
	except discord.HTTPException:
		# Defer error: There is no "thinking" to remove
		# Delete error: No thinking message to delete
		return

def get_subcommand(group: discord.SlashCommandGroup, name: str) -> Optional[discord.SlashCommand | discord.SlashCommandGroup]:
	for cmd in group.subcommands:
		if cmd.name == name:
			return cmd
	return None

def walk_commands_and_groups(cmd):
	yield cmd
	if isinstance(cmd, discord.SlashCommandGroup):
		for subcmd in cmd.subcommands:
			yield from walk_commands_and_groups(subcmd)

async def send_as(ctx: Channelable, webhook = None, *args, **kwargs):
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
	return isinstance(channel, (discord.PartialMessageable, discord.abc.PrivateChannel))

def get_bot_name_in_ctx(ctx: QuasiContext) -> str:
	guild = ctx.guild
	if guild is None:
		if isinstance(ctx, discord.ApplicationContext):
			assert ctx.bot.user is not None # You have already logged in
			return ctx.bot.user.display_name
		else:
			# Interaction without guild
			raise ValueError('Interaction in DM has no information about bot name, call bot.display_name directly.')
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

def generate_config(**kwargs: dict[str, Any]) -> dict[str, Any]:
	result = {}
	for key, d in kwargs.items():
		if d.pop('set_csv', None):
			csv_kwargs = d.pop('csv_kwargs', {})
			d['cast'] = Csv(**csv_kwargs)
		result[key] = config(key, **d)
	return result

__all__ = (
	'EmptyCharacter',
	'check_server_text_channel',
	'autocomplete_get_maid_names',
	'get_guild_channel',
	'send_error_embed',
	'trim',
	'remove_thinking',
	'get_subcommand',
	'walk_commands_and_groups',
	'send_as',
	'proxy',
	'is_DM',
	'get_bot_name_in_ctx',
	'int_to_emoji',
	'generate_config',
)
