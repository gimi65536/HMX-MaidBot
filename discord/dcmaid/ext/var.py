# Let users handle variables for themselves...
import calcs
import discord
from ..basebot import Bot
from ..basecog import BaseCog
from ..utils import *

class Scope:
	_content: discord.User | discord.Guild | discord.abc.GuildChannel

	def __init__(self, content, /):
		self._content = content

	def __hash__(self):
		return hash(self._content)

	def __eq__(self, other):
		if type(self) is type(other):
			return self._content == other._content

		return False

	@property
	def content(self):
		return self._content

class VariableSystem:
	def __init__(self, col = None):
		...

	def add_var(self, name, scope: discord.User | discord.Guild | discord.abc.GuildChannel):
		...

	def retrieve_mapping(self, scope: discord.Member | discord.User) -> dict[calcs.Var, calcs.LValue]:
		# Member: in guild
		# User: only user
		...

	...

class VarCommands(BaseCog, name = 'Var'):
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self._parser = ...
		self._varsystem = ...

	@discord.slash_command(
		description = 'Declare a variable (no side-effects)',
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
