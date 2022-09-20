import discord
import random
from typing import Optional
from ..basebot import Bot
from ..basecog import BaseCog
from ..perm import admin_only

class RollCommands(BaseCog, name = 'Roll'):
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self.db = bot.db
		self.maids = bot.maids
		self.state = bot.state
		self._common_random = random.Random() # Used in DM

	async def cog_before_invoke(self, ctx):
		await self.bot.get_cog('Base').fetch_maids(ctx)

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

	_exec_time_option = discord.Option(
		name = 'number',
		description = 'How many numbers generated (Default 1, up to 100)',
		input_type = int,
		min_value = 1,
		max_value = 100,
		default = 1)

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

	distribution = discord.SlashCommandGroup(
		name = "distribution",
		description = "Random distribution generation"
	)
	set_help(distribution,
		'''
		These commands generates random number under a specific distribution.
		'''
	)

	@distribution.command(
		description = 'Uniform destribution',
		options = [
			discord.Option(
				name = 'lower',
				description = 'Lower bound (Default 0)',
				input_type = float,
				default = 0),
			discord.Option(
				name = 'upper',
				description = 'Upper bound (Default 1)',
				input_type = float,
				default = 1),
			_exec_time_option
		]
	)
	async def uniform(self, ctx, a, b, n):
		'''
		`/{cmd_name} <?lower> <?upper> <?number>` generates `n` random numbers
		with uniform distribution in `[lower, upper)`.

		By default, `lower = 0`, `upper = 1`, `number = 1`.
		'''
		results = (self._get_random_generator(ctx).uniform(a, b) for _ in range(n))
		await ctx.send_response("Uniform [{lower}, {upper}) for {n} times".format(lower = a, upper = b, n = n))
		for result in results:
			await ctx.send_followup(str(result))
			... #followup
		...

def setup(bot):
	bot.add_cog(RollCommands(bot))
