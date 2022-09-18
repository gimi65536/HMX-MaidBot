'''
This module defines basic cogs class that will do some works \
before a cog class is created.
'''
import discord
from typing import List
from .helper import get_help, set_help, update_help
from .reader import load

class BaseCogMeta(discord.CogMeta):
	'''
	Define a cog that automatically supports our help structure and localization.
	'''
	def __new__(mcls, *args, **kwargs):
		cls = super().__new__(mcls, *args, **kwargs)

		commands: List[discord.ApplicationCommand] = cls.__cog_commands__
		d = load(f'help_{ cls.__cog_name__.lower() }')

		for cmd in commands:
			# Make help properties attach on commands
			get_help(cmd)

			if d is None:
				continue
			table = d.get(cmd.name, None)
			update_help(cmd, table)

		... # Do localization (name_localication, etc.) here

		return cls

class BaseCog(discord.Cog, metaclass = BaseCogMeta):
	pass
