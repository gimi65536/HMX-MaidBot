# Let users handle variables for themselves...
import calcs
import discord
import sympy
from ..basebot import Bot
from ..basecog import BaseCog
from ..typing import ChannelType
from ..utils import *
from aiorwlock import RWLock
from sympy import *
from typing import Optional

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

	@property
	def is_user_scope(self):
		return self._is_user

	@property
	def is_guild_scope(self):
		return self._is_guild

	@property
	def is_channel_scope(self):
		return self._is_channel

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

		if col is not None:
			col.create_index({'scope_type': 1, 'scope_id': 1})

		self._managed_scopes: dict[int, Scope] = {} # id: Scope
		self._stored_value: dict[int, tuple[RWLock, dict[str, calcs.Constant]]] = {} # scope_id: (lock, {name: constant})
		...

	async def restore_info(self, bot):
		# Injure all names in SymPy
		for n in dir(sympy):
			if not n.startswith('_'):
				exec(f'{n}=sympy.{n}')

		if col is None:
			return

		info = col.aggregate([
			'$group': {
				'_id': {'scope_type': '$scope_type', 'scope_id': '$scope_id'},
				'vars': {'$push': {'name': '$name', 'type': '$type', 'value': '$value'}}
			}
		])
		for scope_info in info:
			scope_type, scope_id = scope_info['_id']['scope_type'], scope_info['_id']['scope_id']
			try:
				if scope_type == 'user':
					obj = discord.utils.get_or_fetch(bot, 'user', scope_id)
					scope = UserScope(obj)
				elif scope_type == 'channel':
					obj = discord.utils.get_or_fetch(bot, 'channel', scope_id)
					scope = ChannelScope(obj)
				elif scope_type == 'guild':
					obj = discord.utils.get_or_fetch(bot, 'guild', scope_id)
					scope = GuildScope(obj)
				else:
					# Unknown type in the db, but we choose to just omit without dropping.
					continue

				self._managed_scopes[scope_id] = scope
				self._stored_value[scope_id] = (RWLock(), {})
				d: dict[str, calcs.Constant] = self._stored_value[scope_id][1]

				for var in scope_info['vars']:
					name, type, value = var['name'], var['type'], var['value']
					if type == 'number':
						try:
							value = eval(value)
							d[name] = NumberConstant(value)
						except:
							# Unknown error
							pass
					elif type == 'boolean':
						if value.lower() == 'true':
							d[name] = BooleanConstant(True)
						elif value.lower() == 'false':
							d[name] = BooleanConstant(False)
						else:
							# Unknown
							pass
					elif type == 'string':
						d[name] == StringConstant(value)
					else:
						# Unknown to omit
						pass
			except (discord.NotFound, discord.Forbidden):
				# Only drop when the object is unavailable to the bot or disappeared in Discord
				self.col.delete_many({'scope_type': scope_type, 'scope_id': scope_id})
			except:
				continue

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
		bookkeeping: Optional[dict[calcs.LValue, tuple[calcs.Constant, calcs.Constant]]] = None) -> dict[calcs.Var, calcs.LValue]:

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
		var.scope = GuildScope(ctx.channel.guild)

class ToIndividualOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		var.scope = UserScope(ctx.user)

class VarCommands(BaseCog, name = 'Var'):
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self._parser = ...
		self._varsystem = ...

	@discord.Cog.listener()
	async def on_ready(self):
		self._varsystem.restore_info(self.bot)

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
