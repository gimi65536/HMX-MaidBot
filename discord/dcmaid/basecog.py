'''
This module defines basic cogs class that will do some works \
before a cog class is created.
'''
import discord
import json
from .helper import get_help, set_help, update_help

class HelpCog(discord.Cog):
	'''
	Define a cog that automatically supports our help structure.
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		for cmd in self.get_commands():
			# Make help properties attach on commands
			get_help(cmd)

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
			update_help(cmd, table)

class BaseCog(HelpCog):
	pass