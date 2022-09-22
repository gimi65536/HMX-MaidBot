import discord

class MaidNotFound(discord.ApplicationCommandError):
	def __init__(self, falsy_maid_name):
		super().__init__()
		self.falsy_maid_name = falsy_maid_name