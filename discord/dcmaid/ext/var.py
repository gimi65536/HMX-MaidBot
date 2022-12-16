# Let users handle variables for themselves...
import calcs
import discord
import sympy
from ..basebot import Bot
from ..basecog import BaseCog
from ..typing import ChannelType
from ..utils import *
from aiorwlock import RWLock
from itertools import count
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

class BookKeeping(dict[calcs.LValue, tuple[calcs.Constant, calcs.Constant]]):
	_count = count(1)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._order = 0

	def generate_order(self):
		self._order = self._count.next()

	@property
	def order(self):
		return self._order

class VariableSystem:
	def __init__(self, col = None):
		self.col = col

		if col is not None:
			col.create_index({'scope_type': 1, 'scope_id': 1})

		self._managed_scopes: dict[int, Scope] = {} # id: Scope
		self._stored_value: dict[int, tuple[RWLock, dict[str, calcs.Constant]]] = {} # scope_id: (lock, {name: constant})
		self._update_record: dict[int, dict[str, int]] = {} # scope_id: {name: order}

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

				self.add_scope(scope)
				d: dict[str, calcs.Constant] = self._stored_value[scope_id][1]
				r = self._update_record[scope_id]

				for var in scope_info['vars']:
					name, type, value = var['name'], var['type'], var['value']
					if type == 'number':
						try:
							value = eval(value)
							d[name] = calcs.NumberConstant(value)
							r[name] = 0
						except:
							# Unknown error
							pass
					elif type == 'boolean':
						if value.lower() == 'true':
							d[name] = calcs.BooleanConstant(True)
							r[name] = 0
						elif value.lower() == 'false':
							d[name] = calcs.BooleanConstant(False)
							r[name] = 0
						else:
							# Unknown
							pass
					elif type == 'string':
						d[name] == calcs.StringConstant(value)
						r[name] = 0
					else:
						# Unknown to omit
						pass
			except (discord.NotFound, discord.Forbidden):
				# Only drop when the object is unavailable to the bot or disappeared in Discord
				self.col.delete_many({'scope_type': scope_type, 'scope_id': scope_id})
			except:
				continue

	def add_scope(self, scope: Scope) -> Scope:
		if scope.id in self._managed_scopes:
			return self._managed_scopes[scope.id]

		self._managed_scopes[scope.id] = scope
		self._stored_value[scope.id] = (RWLock(), {})
		self._update_record[scope.id] = {}
		return scope

	def add_var(self, name, obj: discord.User | discord.Guild | ChannelType, default: calcs.Constant = calcs.NumberConstant(sympy.Integer(0))):
		# Is this method needs writer lock?
		match obj:
			case discord.User():
				scope = self.add_scope(UserScope(obj))
			case discord.Guild():
				scope = self.add_scope(GuildScope(obj))
			case _:
				scope = self.add_scope(ChannelScope(obj))

		if name in self._stored_value[scope.id][1]:
			# raise ValueError(f'Variable {name} has been declared before!')
			return

		self._stored_value[scope.id][1][name] = default
		self._update_record[scope.id][name] = 0

		if self.col is not None:
			self.col.insert_one(self.scope_to_document(scope) | {'name': name} | self.constant_to_document(default))

	async def retrieve_mapping(self,
		caller: discord.User,
		channel: ChannelType,
		bookkeeping: Optional[dict[calcs.LValue, tuple[calcs.Constant, calcs.Constant]]] = None) -> dict[calcs.Var, calcs.LValue]:

		if isinstance(bookkeeping, BookKeeping):
			bookkeeping.generate_order()

		result: dict[calcs.Var, calcs.LValue] = {}

		scopes = []
		# user scope
		scopes.append(self.add_scope(UserScope(caller)))
		# thread scope
		if isinstance(channel, discord.Thread):
			scopes.append(self.add_scope(ChannelScope(channel)))
		# channel scope
		if isinstance(channel, discord.Thread):
			scopes.append(self.add_scope(ChannelScope(channel.channel)))
		else:
			scopes.append(self.add_scope(ChannelScope(channel)))
		# guild scope
		if not is_DM(channel):
			scopes.append(self.add_scope(GuildScope(channel.guild)))

		for scope in scopes:
			d: dict[str, calcs.Constant]
			lock, d = self._stored_value[scope.id]
			async with lock.read:
				for name, constant in d.items():
					var = calcs.Var(name, scope)
					lv = calcs.LValue(var, constant, bookkeeping)
					result[var] = lv

		return result

	async def update_bookkeeping(self, bookkeeping: dict[calcs.LValue, tuple[calcs.Constant, calcs.Constant]]):
		# @Pre the permission checks are done
		# The method only updates directly
		# If the bookkeeping is an original dict, the update is forcely done, or the BookKeeping.order is taken into account.
		table: dict[int, list[calcs.LValue]] = {}
		for lv in bookkeeping:
			if lv.var.scope.id not in table:
				table[lv.var.scope.id] = []
			table[lv.var.scope.id].append(lv)

		for scope_id, lvs in table.items():
			lock, d = self._stored_value[scope_id]
			r = self._update_record[scope_id]
			async with lock.write:
				for lv in lvs:
					name = lv.var.name
					if isinstance(bookkeeping, BookKeeping) and r[name] >= bookkeeping.order:
						continue

					f, t = bookkeeping[lv]
					d[name] = t
					if isinstance(bookkeeping, BookKeeping):
						r[name] = bookkeeping.order

					if self.col is not None:
						self.col.update_one({'scope_id': scope_id, 'name': name}, self.constant_to_document(t))

	@staticmethod
	def scope_to_document(scope: Scope):
		if scope.is_user:
			return {'scope_id': scope.id, 'scope_type': 'user'}
		elif scope.is_guild:
			return {'scope_id': scope.id, 'scope_type': 'guild'}
		elif scope.is_channel:
			return {'scope_id': scope.id, 'scope_type': 'channel'}
		raise ValueError('Unknown scope type when converting into document')

	@staticmethod
	def constant_to_document(const: calcs.Constant):
		if const.is_number:
			return {'type': 'number', 'value': sympy.srepr(const.value)}
		elif const.is_bool:
			return {'type': 'boolean', 'value': str(const.value).lower()}
		else:
			return {'type': 'string', 'value': const.value}

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
