import discord
import random
from discord.ext.pages import Page, Paginator
from importlib import import_module
from more_itertools import peekable, spy
from rollgames import (
	ArgumentLengthError as ALE,
	ArgumentTypeError as ATE,
	GameNotFound as GNF
)
from typing import Dict, List, Optional
from ..basebot import Bot
from ..basecog import BaseCog
from ..constants import MAX_FIELDS_IN_EMBED
from ..helper import set_help
from ..perm import admin_only
from ..utils import *

class RollCommands(BaseCog, name = 'Roll'):
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self.db = bot.db
		self.maids = bot.maids
		self.state = bot.state
		self._common_random = random.Random() # Used in DM
		self._help_pages: Dict[str, Paginator] = {}

	async def cog_before_invoke(self, ctx):
		if is_DM(ctx.channel):
			return

		maid_webhook = await self.bot.get_cog('Base').fetch_maids(get_guild_channel(ctx.channel))
		maid_weights = self.bot.get_cog('Base').fetch_weight(get_guild_channel(ctx.channel))
		setattr(ctx, 'maid_webhook', maid_webhook)
		setattr(ctx, 'maid_weights', maid_weights)

	async def _get_webhook_by_name(self, ctx, maid_name):
		if is_DM(ctx.channel):
			webhook = None
		else:
			if hasattr(ctx, 'maid_webhook'):
				maid_webhook = ctx.maid_webhook
			else:
				maid_webhook = await self.bot.get_cog('Base').fetch_maids(get_guild_channel(ctx.channel))

			webhook = maid_webhook.get(maid, None)

		return webhook

	# Since webhooks cannot really reply or followup messages as a bot,
	# here we simulate those with plain messages whoever the sender is.
	async def _send_followup(self, ctx, maid, *args, **kwargs):
		webhook = await self._get_webhook_by_name(ctx, maid)
		await send_as(ctx, webhook, *args, **kwargs)

	@staticmethod
	def _list_message(l):
		l = list(l)
		max_digit = len(str(len(l)))
		l = [f"{i:{max_digit}}: {e}" for i, e in enumerate(l, 1)]
		return '\n'.join(l)

	@classmethod
	def _build_box_message(cls, ctx, tran_key, l, /, **kwargs):
		return f'<@{ctx.author.id}>\n```\n{cls._trans(ctx, tran_key, format = kwargs)}\n{cls._list_message(l)}```'

	__state_random_key__ = 'random_generator_{}'

	def _get_random_generator(self, ctx) -> random.Random:
		channel = ctx.channel
		if is_DM(channel):
			return self._common_random

		channel = get_guild_channel(channel)
		generator = self.state.get(self.__state_random_key__.format(channel.id))
		if generator is None:
			generator = random.Random()
			self.state.set(self.__state_random_key__.format(channel.id), generator)

		return generator

	_exec_time_option = discord.Option(int,
		name = 'number',
		description = 'How many numbers generated (Default 1, up to 50)',
		min_value = 1,
		max_value = 50,
		default = 1)

	@discord.commands.slash_command(
		description = 'Set or reset the seed of the random generator of the channel',
		default_member_permissions = admin_only,
		guild_only = True,
		options = [
			discord.Option(str,
				name = 'seed',
				description = 'Random seed (Optional)',
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

	def _random_maid(self, ctx):
		maid = None
		if hasattr(ctx, 'maid_weights'):
			maid = ctx.maid_weights.random_get(self._get_random_generator(ctx))
		return maid

	distribution = discord.SlashCommandGroup(
		name = "distribution",
		description = "Random distribution generation"
	)
	set_help(distribution,
		'''
		These commands generates random number under a specific distribution.
		'''
	)

	async def _dist(self, ctx, results, tran_key, /, **kwargs):
		await remove_thinking(ctx)
		message = self._build_box_message(ctx, tran_key, results, **kwargs)
		maid = self._random_maid(ctx)
		await self._send_followup(ctx, maid, message)

	@distribution.command(
		description = 'Uniform destribution',
		options = [
			discord.Option(float,
				name = 'lower',
				description = 'Lower bound (Default 0)',
				default = 0),
			discord.Option(float,
				name = 'upper',
				description = 'Upper bound (Default 1)',
				default = 1),
			_exec_time_option
		]
	)
	async def uniform(self, ctx, a, b, n):
		'''
		`/{cmd_name} <?lower> <?upper> <?number>` generates `n` random numbers
		with uniform distribution in `[lower, upper]`.

		By default, `lower = 0`, `upper = 1`, `number = 1`.
		'''
		results = (self._get_random_generator(ctx).uniform(a, b) for _ in range(n))
		await self._dist(ctx, results, 'dist-uniform', lower = a, upper = b, n = n)

	@distribution.command(
		description = 'Random integer',
		options = [
			discord.Option(int,
				name = 'lower',
				description = 'Lower bound (Default 0)',
				default = 0),
			discord.Option(int,
				name = 'upper',
				description = 'Upper bound (Default 1)',
				default = 1),
			_exec_time_option
		]
	)
	async def randint(self, ctx, a, b, n):
		'''
		`/{cmd_name} <?lower> <?upper> <?number>` generates `n` random integers
		fairly in `[lower, upper]`.

		By default, `lower = 0`, `upper = 1`, `number = 1`.
		'''
		results = (self._get_random_generator(ctx).randint(a, b) for _ in range(n))
		await self._dist(ctx, results, 'dist-randint', lower = a, upper = b, n = n)

	@distribution.command(
		description = 'Triangular distribution',
		options = [
			discord.Option(float,
				name = 'lower',
				description = 'Lower bound (Default 0)',
				default = 0),
			discord.Option(float,
				name = 'mode',
				description = 'Mode (Default 0.5)',
				default = 0.5),
			discord.Option(float,
				name = 'upper',
				description = 'Upper bound (Default 1)',
				default = 1),
			_exec_time_option
		]
	)
	async def triangular(self, ctx, a, m, b, n):
		'''
		`/{cmd_name} <?lower> <?upper> <?number>` generates `n` random numbers
		with triangular distribution in `[lower, upper]`.

		By default, `lower = 0`, `mode = 0.5`, `upper = 1`, `number = 1`.
		'''
		results = (self._get_random_generator(ctx).triangular(a, b, m) for _ in range(n))
		await self._dist(ctx, results, 'dist-triangular', lower = a, mode = m, upper = b, n = n)

	async def beta(self, ctx, a, b, n):
		NotImplemented

	async def exponential(self, ctx, l, n):
		NotImplemented

	async def gamma(self, ctx, a, b, n):
		NotImplemented

	async def lognormal(self, ctx, m, s, n):
		NotImplemented

	async def normal(self, ctx, m, s, n):
		NotImplemented

	async def vonmises(self, ctx, m, s, n):
		NotImplemented

	async def pareto(self, ctx, a, n):
		NotImplemented

	async def weibull(self, ctx, a, b, n):
		NotImplemented

	async def cog_command_error(self, ctx, exception: discord.ApplicationCommandError):
		match exception:
			case ArgumentLengthError():
				lens = ', '.join([str(i) for i in exception.expect])
				await send_error_embed(ctx,
					name = self._trans(ctx, 'argument-length-error'),
					value = self._trans(ctx, 'argument-length-error-value', format = {'lens': lens, 'len': exception.got}),
					ephemeral = True
				)
			case ArgumentTypeError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'argument-type-error'),
					value = self._trans(ctx, 'argument-type-error-value', format = {'order': exception.order, 't': exception.t.__name__, 'got': exception.got}),
					ephemeral = True
				)
			case GameNotFound():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'game-name-error'),
					value = self._trans(ctx, 'game-name-error-value', format = {'name': exception.name}),
					ephemeral = True
				)
			case _:
				# Propagate
				super().cog_command_error(ctx, exception)

	game_group = discord.SlashCommandGroup(
		name = "game",
		description = "Play a randomness game with maids!"
	)
	set_help(game_group,
		'''
		Use these commands to play games.
		'''
	)

	@game_group.command(
		name = 'help',
		description = 'Get the help of games we have',
		options = [
			discord.Option(str,
				name = 'game',
				description = 'Name of the game (Optional)',
				default = None)
		]
	)
	async def game_help(self, ctx, game_name):
		'''
		`/{cmd_name} <?game name>` gives the help of the specific game,
		or lists all the games we have if the game name is not given.
		'''
		if game_name is None:
			game_name = ''
		game_name = trim(game_name)
		if game_name != '' and game_name not in ext_roll.all_mapping_table:
			raise GameNotFound(game_name)

		locale = ctx.locale
		if game_name == '':
			if locale in self._help_pages:
				await self._help_pages[locale].respond(ctx.interaction)
				return
			pages = []
			remains = peekable(ext_roll.registered_games.items())
			while remains:
				listed_items, remains = spy(remains, MAX_FIELDS_IN_EMBED)
				remains = peekable(remains)
				embed = discord.Embed(title = self._trans(ctx, 'game-list'), description = self._trans(ctx, 'game-list-description'))

				for name, game_cls in listed_items:
					game_data = game_cls.game_data
					embed.add_field(name = name, value = f'`{game_data.get_name(locale)}` {game_data.get_description(locale)}')

				pages.append(Page(embeds = [embed]))

			self._help_pages[locale] = Paginator(pages = pages)
			await self._help_pages[locale].respond(ctx.interaction)
		else:
			...

	@game_group.command(
		description = 'Play the game',
		options = [
			discord.Option(str,
				name = 'game',
				description = 'Name of the game'),
			discord.Option(str,
				name = 'arguments',
				description = "Pass argument (May be optional)",
				default = None)
		]
	)
	async def play(self, ctx, game_name, arguments):
		'''
		`/{cmd_name} <game name> <args>` play a game with given arguments.
		The arguments are separated by whitespaces.
		If you want to pass an empty string, use `""`; if you want to pass
		an argument containing spaces or double-quotes, put them into `""`s
		and use `\\"` to indicate a double-quote.
		'''
		game_name = trim(game_name)
		if game_name not in ext_roll.all_mapping_table:
			raise GameNotFound(game_name)

		game_cls = ext_roll.all_mapping_table[game_name]
		game_data = game_cls.game_data
		maid = self._random_maid(ctx)
		webhook = await self._get_webhook_by_name(maid)
		try:
			game = game_cls(
				ctx,
				webhook,
				arguments,
				self._get_random_generator(ctx),
				self._trans(ctx, 'game-play-initial-text', format = {'id': ctx.author.id, 'game': game_data.get_name(ctx.locale)})
			)
		except ALE as e:
			raise ArgumentLengthError(e.expect, e.got)
		except ATE as e:
			raise ArgumentTypeError(e.order, e.t, e.got)

		await game.run()

	def load_game_ext(self, ext):
		self._help_pages = {}
		import_module(ext, ext_roll.__name__)

	def load_game_exts(self, exts):
		self._help_pages = {}
		for ext in exts:
			import_module(ext, ext_roll.__name__)

class ArgumentLengthError(ALE, discord.ApplicationCommandError):
	pass

class ArgumentTypeError(ATE, discord.ApplicationCommandError):
	pass

class GameNotFound(GNF, discord.ApplicationCommandError):
	pass

ext_roll = import_module('.ext-roll', __package__)

def setup(bot):
	bot.add_cog(RollCommands(bot))
