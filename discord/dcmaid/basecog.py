'''
This module defines basic cogs class that will do some works \
before a cog class is created.
'''
import discord
from typing import List
from .helper import get_help, set_help, update_help
from .reader import load

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

		commands: List[discord.ApplicationCommand] = cls.__cog_commands__

		for cmd in commands:
			# Make help properties attach on commands
			get_help(cmd)

		d = load(f'{ cls.__cog_name__.lower() }')

		if d is None:
			return cls

		for cmd in commands:
			cmd_locale = d.get(cmd.name, {})

			# Do help localization here
			help_table = cmd_locale.get('help', None)
			update_help(cmd, help_table)

			# Do localization (name_localication, etc.) here
			if isinstance(cmd, discord.SlashCommand) or isinstance(cmd, discord.SlashCommandGroup):
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

			... # Do embed localization??

		return cls

class BaseCog(discord.Cog, metaclass = BaseCogMeta):
	pass
