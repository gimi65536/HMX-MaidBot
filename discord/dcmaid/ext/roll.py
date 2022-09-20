import discord
import random
from typing import Optional
from ..basecog import BaseCog
from ..perm import admin_only

class RollCommands(BaseCog, name = 'Roll'):
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self.db = bot.db
		self.maids = bot.maids
		self.state = bot.state
		self._common_random = random.Random() # Used in DM

	__state_random_key__ = 'random_generator_{}'

	def _get_random_generator(self, ctx) -> random.Random:
		channel = ctx.channel
		if isinstance(channel, (discord.PartialMessageable, discord.DMChannel)):
			return self._common_random

		channel = get_guild_channel(channel)
		generator = self.state.get(self.__state_random_key__.format(channel.id))
		if generator is None:
			generator = random.Random()
			self.state.set(self.__state_random_key__.format(channel.id), generator)

		return generator

	@discord.commands.slash_command(
		description = 'Set or reset the seed of the random generator of the channel',
		default_member_permissions = admin_only,
		guild_only = True,
		options = [
			discord.Option(
				name = 'seed',
				description = 'Random seed (Optional)',
				input_type = str,
				default = None)
		]
	)
	async def seed(self, ctx, seed: Optional[str]):
		'''
		`/seed <?seed>` sets the seed number of the random generator for the guild channel.
		This command is for OPs only.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		channel = get_guild_channel(ctx.channel)
		generator = random.Random(seed)
		self.state.set(self.__state_random_key__.format(channel.id), generator)

		await ctx.send_response(
			content = self._trans(ctx, 'seed-set'),
			ephemeral = True
		)