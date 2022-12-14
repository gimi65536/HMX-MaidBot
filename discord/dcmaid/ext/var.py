# Let users handle variables for themselves...
import calcs
import discord
from ..basebot import Bot
from ..basecog import BaseCog
from ..utils import *
from typing import Generic, TypeAlias, TypeVar

Messageable: TypeAlias = (
	discord.abc.GuildChannel |
	discord.abc.PrivateChannel |
	discord.Thread
)

ScopedType = TypeVar('ScopedType',
	discord.User,
	discord.Guild,
	Messageable
)

class Scope(Generic[ScopedType]):
	_content: ScopedType

	_is_user: bool = False
	_is_guild: bool = False
	_is_channel: bool = False

	def __init__(self, content: Messageable, /):
		self._content = content

	def __hash__(self):
		return hash(self._content)

	def __eq__(self, other):
		if type(self) is type(other):
			return self._content.id == other._content.id

		return False

	@property
	def content(self):
		return self._content

	@property
	def is_user_scope(self):
		return self._is_user

	@property
	def is_guild_scope(self):
		return self._is_guild

	@property
	def is_channel_scope(self):
		return self._is_channel

class UserScope(Scope[discord.User]):
	_is_user = True
	def __init__(self, content, /):
		super().__init__(content)

class GuildScope(Scope[discord.Guild]):
	_is_guild = True
	def __init__(self, content, /):
		super().__init__(content)

class ChannelScope(Scope[Messageable]):
	_is_channel = True
	def __init__(self, content: Messageable, /):
		super().__init__(content)

class VariableSystem:
	def __init__(self, col = None):
		self.col = col

		self._restore_info = []

		if col is not None:
			self._restore_info = col.find()

	@property
	def restore_info(self):
		return iter(self._restore_info)

	def add_var(self, name, scope: discord.User | discord.Guild | discord.abc.GuildChannel):
		...

	def retrieve_mapping(self,
		scope: discord.Member | discord.User,
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

class ToChannelOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		var.scope = ChannelScope(channel)

class ToGuildOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
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
