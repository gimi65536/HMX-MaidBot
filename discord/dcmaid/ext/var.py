# Let users handle variables for themselves...
import calcs
import discord
from ..basebot import Bot
from ..basecog import BaseCog
from ..typing import ChannelType
from ..utils import *

class Scope:
	_id: int
	_is_user: bool = False
	_is_guild: bool = False
	_is_channel: bool = False

	def __init__(self, id_or_obj: int | discord.Snowflake, /):
		if isinstance(id_or_obj, int):
			self._id = id_or_obj
		else:
			self._id = id_or_obj.id

	def __hash__(self):
		return hash(self._id)

	def __eq__(self, other):
		# @pre: ids of different types of object 
		if type(self) is type(other):
			return self._id == other._id

		return False

	@property
	def id(self):
		return self._id

class UserScope(Scope):
	_is_user = True

class GuildScope(Scope):
	_is_guild = True

# Every channel/thread that can be fetched by bot.fetch_channel()
class ChannelScope(Scope):
	_is_channel = True

class VariableSystem:
	def __init__(self, col = None):
		self.col = col

		self._restore_info = []

		if col is not None:
			self._restore_info = col.find()

	@property
	def restore_info(self):
		return iter(self._restore_info)

	def add_var(self, name, scope: discord.User | discord.Guild | ChannelType):
		match scope:
			case discord.User():
				...
			case discord.Guild():
				...
			case _:
				...
		...

	def retrieve_mapping(self,
		caller: discord.User,
		channel: ChannelType,
		bookkeeping: dict[calcs.LValue, tuple[calcs.Constant, calcs.Constant]]) -> dict[calcs.Var, calcs.LValue]:
		# Member: in guild
		# User: only user
		...

	...

class _ChangeScopeOperator(calcs.UnaryOperator):
	def eval(self, mapping, **kwargs):
		node = self._operands[0]
		if isinstance(node, calcs.Var):
			self._cast_scope(node, kwargs['bot'], kwargs['ctx'])
			return node.eval(mapping, **kwargs)

		raise ValueError('Only applied on variables')

	def _cast_scope(self, var: calcs.Var, bot: Bot, ctx):
		raise NotImplementedError

class ToThreadOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if not isinstance(ctx.channel, discord.Thread):
			raise ValueError('Not in thread')
		var.scope = ChannelScope(ctx.channel)

class ToChannelOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if isinstance(ctx.channel, discord.Thread):
			var.scope = ChannelScope(ctx.channel.channel)
		else:
			var.scope = ChannelScope(ctx.channel)

class ToGuildOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if is_DM(ctx.channel):
			raise ValueError('Not in guild')
		var.scope = GuildScope(channel.guild)

class VarCommands(BaseCog, name = 'Var'):
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self._parser = ...
		self._varsystem = ...

	@discord.slash_command(
		description = 'Declare your own variable (no side-effects)',
		options = [
			discord.Option(str,
				name = 'name',
				description = 'Name of the variable'),
			discord.Option(str,
				name = 'value',
				description = 'Value of the variable (Default to integer 0)',
				default = '0')
		]
	)
	async def declare(self, ctx, name, value):
		try:
			expr = self._parser.parse(value)
		except Exception as e:
			raise ParseError(e)

		try:
			n = expr.eval(...)
		except Exception as e:
			raise CalculatorError(e)

		...

	async def cog_command_error(self, ctx, exception: discord.ApplicationCommandError):
		match exception:
			case ParseError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'parse-error'),
					value = self._trans(ctx, 'parse-error-value', format = {'type': type(exception.e).__name__, 'text': str(exception.e)}),
					ephemeral = True
				)
			case CalculatorError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'calcs-error'),
					value = self._trans(ctx, 'calcs-error-value', format = {'type': type(exception.e).__name__, 'text': str(exception.e)}),
					ephemeral = True
				)
			case _:
				# Propagate
				await super().cog_command_error(ctx, exception)

class ParseError(discord.ApplicationCommandError):
	def __init__(self, e):
		self.e = e

class CalculatorError(discord.ApplicationCommandError):
	def __init__(self, e):
		self.e = e

def setup(bot):
	bot.add_cog(VarCommands(bot))
