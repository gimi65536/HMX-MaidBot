'''
This module defines basic cogs class that will do some works \
before a cog class is created.
'''
import discord
from importlib_resources import files
from reader import load
from typing import Optional
from .basebot import Bot
from .exception import MaidNotFound
from .helper import get_help, update_help
from .typing import Localeable
from .utils import *

def _replace_localization(obj, attr: str, attr_locale: str, key: str, cmd_locale: dict):
	table = cmd_locale.get(key, {})
	if None in table: # Get the overriden default
		setattr(obj, attr, table.pop(None))
	setattr(obj, attr_locale, table)

class BaseCogMeta(discord.CogMeta):
	'''
	Define a cog that automatically supports our help structure and localization.
	'''

	_common_table: dict[Optional[str], dict[Optional[str], str]] = None

	def __new__(mcls, *args, **kwargs):
		cls = super().__new__(mcls, *args, **kwargs)

		commands: list[discord.ApplicationCommand] = []
		for cmd in cls.__cog_commands__:
			commands.extend(walk_commands_and_groups(cmd))

		for cmd in commands:
			# Make help properties attach on commands
			get_help(cmd)

		# Load common table
		base_path = files(__package__).joinpath('locale')

		if mcls._common_table is None:
			common_d = load(base_path / '_common')
			if common_d is None:
				mcls._common_table = {}
			else:
				mcls._common_table = common_d.get('__translation_table', {})

		cls.__cog_translation_table__: dict[Optional[str], dict[Optional[str], str]] = mcls._common_table.copy()

		# Load specific table
		d = load(base_path / f'{ cls.__cog_name__.lower() }')

		if d is None:
			return cls

		cls.__cog_translation_table__.update(d.get('__translation_table', {}))

		for cmd in commands:
			cmd_locale = d.get(cmd.qualified_name, {})

			# Do help localization here
			help_table = cmd_locale.get('help', {})
			update_help(cmd, help_table)

			# Do localization (name_localication, etc.) here
			if isinstance(cmd, (discord.SlashCommand, discord.SlashCommandGroup)):
				''' # The original code for reference
				name_table = cmd_locale.get('name', {})
				if None in name_table: # Get the overriden default
					cmd.name = name_table.pop(None)
				cmd.name_localizations = name_table
				'''
				_replace_localization(cmd, 'name', 'name_localizations', 'name', cmd_locale)
				_replace_localization(cmd, 'description', 'description_localizations', 'description', cmd_locale)

			# Do option localization here
			if isinstance(cmd, discord.SlashCommand):
				options: list[discord.Option] = cmd.options
				for option in options:
					_replace_localization(option, 'name', 'name_localizations', f'{ option.name }.name', cmd_locale)
					_replace_localization(option, 'description', 'description_localizations', f'{ option.name }.description', cmd_locale)

					# If using autocomplete, then localization is handled by autocomplete
					choices = option.choices
					if choices is None:
						choices = []
					for choice in choices:
						if not isinstance(choice, discord.OptionChoice):
							continue
						_replace_localization(choice, 'name', 'name_localizations', f'{ option.name }.choice.{ choice.name }', cmd_locale)

		return cls

class BaseCog(discord.Cog, metaclass = BaseCogMeta):
	# Notice that we only accept the bot of '.basebot.Bot' class or its subclasses.
	def __init__(self, bot: Bot):
		if not isinstance(bot, Bot):
			raise TypeError('Only accepts basebot.Bot type.')

		super().__init__()
		self.bot = bot
		self.db = bot.db
		self.maids = bot.maids
		self.state = bot.state

	async def cog_command_error(self, ctx, exception: discord.ApplicationCommandError):
		if isinstance(exception, MaidNotFound):
			await send_error_embed(ctx,
				name = self._trans(ctx, 'no-maid'),
				value = self._trans(ctx, 'no-maid-value', format = {'maid_name': exception.falsy_maid_name}),
				ephemeral = True
			)
		else:
			# Propagate
			raise exception

	# Given a complex dictionary which every key is optional string and every element is either
	# a string or a complex dictionary and given keys, return the string if any.
	# If a key does not exist, the function tries to retrieve None key.
	@staticmethod
	def _get_nested_str(d: dict, *args: str, default: Optional[str] = None, format: dict[str, str] = {}) -> Optional[str]:
		now = d
		args = list(reversed(args))
		while len(args) > 0:
			key = args.pop()
			if isinstance(now, dict):
				# If the key does not exist, try to retrieve "None" key
				now = now.get(key, now.get(None, {}))
			else:
				# Get too many keys
				now = {}
		if isinstance(now, dict):
			# Not fully expanded
			return default
		else:
			return now.format(**format)

	@classmethod
	def _trans(cls,
		locale_or_localeable: str | Localeable,
		*args: str,
		default: Optional[str] = None,
		format: dict[str, str] = {}) -> Optional[str]:

		table = cls.__cog_translation_table__
		if isinstance(locale_or_localeable, str):
			return cls._get_nested_str(table, *args, locale_or_localeable, default = default, format = format)
		else:
			return cls._get_nested_str(table, *args, locale_or_localeable.locale, default = default, format = format)

__all__ = ('BaseCogMeta', 'BaseCog')
