'''
This module defines basic cogs class that will do some works \
before a cog class is created.
'''
import discord
from typing import Dict, List, Optional, Union
from .basebot import Bot
from .helper import get_help, set_help, update_help
from .reader import load
from .typing import Localeable

def _replace_localization(obj, attr: str, attr_locale: str, key: str, cmd_locale: dict):
	table = cmd_locale.get(key, {})
	if None in table: # Get the overriden default
		setattr(obj, attr, table.pop(None))
	setattr(obj, attr_locale, table)

class BaseCogMeta(discord.CogMeta):
	'''
	Define a cog that automatically supports our help structure and localization.
	'''
	def __new__(mcls, *args, **kwargs):
		cls = super().__new__(mcls, *args, **kwargs)

		commands: List[discord.ApplicationCommand] = []
		for cmd in cls.__cog_commands__:
			if isinstance(cmd, discord.SlashCommandGroup):
				commands.extend(cmd.walk_commands())
			else:
				commands.append(cmd)

		for cmd in commands:
			# Make help properties attach on commands
			get_help(cmd)

		d = load(f'{ cls.__cog_name__.lower() }')

		if d is None:
			return cls

		cls.__cog_translation_table__: Dict[Optional[str], Dict[Optional[str], str]] = d.get('__translation_table', {})

		for cmd in commands:
			cmd_locale = d.get(cmd.qualified_name, {})

			# Do help localization here
			help_table = cmd_locale.get('help', None)
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
				options: List[discord.Option] = cmd.options
				for option in options:
					_replace_localization(option, 'name', 'name_localizations', f'{ option.name }.name', cmd_locale)
					_replace_localization(option, 'description', 'description_localizations', f'{ option.name }.description', cmd_locale)

					# If using autocomplete, then localization is handled by autocomplete
					choices = option.choices
					if choices is not None:
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

	# Given a complex dictionary which every key is optional string and every element is either
	# a string or a complex dictionary and given keys, return the string if any.
	# If a key does not exist, the function tries to retrieve None key.
	@staticmethod
	def _get_nested_str(d: dict, *args: str, default: Optional[str] = None, format: Dict[str, str] = {}) -> Optional[str]:
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
		locale_or_localeable: Union[str, Localeable],
		*args: str,
		default: Optional[str] = None,
		format: Dict[str, str] = {}) -> Optional[str]:

		table = cls.__cog_translation_table__
		if isinstance(locale_or_localeable, str):
			return cls._get_nested_str(table, *args, locale_or_localeable, default = default, format = format)
		else:
			return cls._get_nested_str(table, *args, locale_or_localeable.locale, default = default, format = format)

__all__ = ('BaseCogMeta', 'BaseCog')
