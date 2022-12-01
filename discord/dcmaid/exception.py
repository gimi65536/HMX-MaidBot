import discord

class DependentCogNotLoaded(Exception):
	def __init__(self, dependency, lost):
		super().__init__(
			f'The cog should be loaded after all the cogs: {dependency} are loaded, '
			f'but the {lost} cog has not been loaded.'
		)

class MaidNotFound(discord.ApplicationCommandError):
	def __init__(self, falsy_maid_name):
		super().__init__()
		self.falsy_maid_name = falsy_maid_name