'''
This module defines basic cogs class that will do some works \
before a cog class is created.
'''
import discord
import json
from .helper import get_help, set_help

class HelpCog(discord.Cog):
	'''
	Define a cog that automatically supports our help structure.
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		for cmd in self.get_commands():
			# Make help properties attach on commands
			get_help(cmd)

		self._help_locale = kwargs.get('locale', None)
		if self._help_locale is None:
			return

		try:
			fp = open(f'help_{ self.qualified_name.lower() }.json')
		except:
			return

		d = json.load(fp)
		fp.close()

		for cmd in self.get_commands():
			table = d.get(cmd.name, None)
			if table is None:
				continue
			localization_help = table.get(self._help_locale, None)
			if localization_help is None:
				continue
			set_help(cmd, localization_help)

class BaseCog(HelpCog):
	pass