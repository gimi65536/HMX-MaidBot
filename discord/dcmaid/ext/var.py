# Let users handle variables for themselves...
import calcs
import discord
import re
import sympy
from ..basebot import Bot
from ..basecog import BaseCog
from ..typing import ChannelType, QuasiContext
from ..utils import *
from aiorwlock import RWLock
from asyncio import get_running_loop
from itertools import count
from sympy import *
from typing import Optional

config = generate_config(
	EXT_VAR_DB_BASED = {'default': False, 'cast': bool},
	EXT_VAR_DB_COLLECTION = {'default': 'var_system'},
)

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

class BookKeeping(dict[calcs.Var, tuple[calcs.Constant, calcs.Constant]]):
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
			col.create_index({'scope_type': 1, 'scope_id': 1, 'name': 1})

		self._managed_scopes: dict[int, Scope] = {} # id: Scope
		self._stored_value: dict[int, tuple[RWLock, dict[str, calcs.Constant]]] = {} # scope_id: (lock, {name: constant})
		self._update_record: dict[int, dict[str, int]] = {} # scope_id: {name: order}

	@staticmethod
	def to_var(name: str, obj) -> calcs.Var:
		match obj:
			case discord.User() | discord.Member():
				scope = self.add_scope(UserScope(obj))
			case discord.Guild():
				scope = self.add_scope(GuildScope(obj))
			case _:
				scope = self.add_scope(ChannelScope(obj))

		return calcs.Var(name, scope)

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

	async def add_var(self, name, obj: discord.User | discord.Member | discord.Guild | ChannelType, default: calcs.Constant = calcs.NumberConstant(sympy.Integer(0))) -> bool:
		match obj:
			case discord.User() | discord.Member():
				scope = self.add_scope(UserScope(obj))
			case discord.Guild():
				scope = self.add_scope(GuildScope(obj))
			case _:
				scope = self.add_scope(ChannelScope(obj))

		lock, d = self._stored_value[scope.id]

		with lock.write:
			if name in self._stored_value[scope.id][1]:
				# raise ValueError(f'Variable {name} has been declared before!')
				return False

			d[1][name] = default
			self._update_record[scope.id][name] = 0

			if self.col is not None:
				self.col.insert_one(self.scope_to_document(scope) | {'name': name} | self.constant_to_document(default))

			return True

	def exist_var(self, name, obj: discord.User | discord.Member | discord.Guild | ChannelType) -> bool:
		match obj:
			case discord.User() | discord.Member():
				scope = self.add_scope(UserScope(obj))
			case discord.Guild():
				scope = self.add_scope(GuildScope(obj))
			case _:
				scope = self.add_scope(ChannelScope(obj))

		_, d = self._stored_value[scope.id]
		return name in d

	async def retrieve_mapping(self,
		caller: discord.User | discord.Member,
		channel: ChannelType,
		bookkeeping: Optional[dict[calcs.Var, tuple[calcs.Constant, calcs.Constant]]] = None) -> dict[calcs.Var, calcs.LValue]:

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
		scopes.append(self.add_scope(ChannelScope(get_guild_channel(channel))))
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

	# This method is valid ONLY IF the "from" value in bookkeeping is not meaningful in update_bookkeeping()
	async def update_var(self, var: calcs.Var, value: calcs.Constant, bookkeeping_order: Optional[int] = None) -> bool:
		if bookkeeping_order is None:
			bookkeeping = {}
		else:
			bookkeeping = BookKeeping()
			bookkeeping._order = bookkeeping_order

		bookkeeping[var] = (calcs.NumberConstant(sympy.Integer(0)), value)
		result = await self.update_bookkeeping(bookkeeping)
		return result[var]

	async def update_bookkeeping(self, bookkeeping: dict[calcs.Var, tuple[calcs.Constant, calcs.Constant]]) -> dict[calcs.Var, bool]:
		# @Pre the permission checks are done
		# The method only updates directly
		# If the bookkeeping is an original dict, the update is forcely done, or the BookKeeping.order is taken into account.
		table: dict[int, list[calcs.Var]] = {}
		for var in bookkeeping:
			if var.scope.id not in table:
				table[var.scope.id] = []
			table[var.scope.id].append(var)

		result: dict[calcs.Var, bool] = {}
		for scope_id, vars in table.items():
			lock, d = self._stored_value[scope_id]
			r = self._update_record[scope_id]
			async with lock.write:
				for var in vars:
					name = var.name
					if isinstance(bookkeeping, BookKeeping) and r[name] >= bookkeeping.order:
						result[var] = False
						continue
					result[var] = True

					f, t = bookkeeping[var]
					d[name] = t
					if isinstance(bookkeeping, BookKeeping):
						r[name] = bookkeeping.order

					if self.col is not None:
						self.col.update_one({'scope_id': scope_id, 'name': name}, self.constant_to_document(t))

		return result

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
		var.scope = ChannelScope(get_guild_channel(ctx.channel))

class ToGuildOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if is_DM(ctx.channel):
			raise ValueError('Not in guild')
		var.scope = GuildScope(ctx.channel.guild)

class ToIndividualOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		var.scope = UserScope(ctx.user)

_eval_prefix = '=$'

class VarCommands(BaseCog, name = 'Var'):
	_backticks = re.compile('`(?=`)|`$')
	_varname = re.compile(r'\w+')

	def __init__(self, bot: Bot):
		super().__init__(bot)
		self._parser = ...
		self._var_col = bot.db[config['EXT_VAR_DB_COLLECTION']] if config['EXT_VAR_DB_BASED'] else None
		self._varsystem: VariableSystem = VariableSystem(self._var_col)

	@discord.Cog.listener()
	async def on_ready(self):
		self._varsystem.restore_info(self.bot)

	@staticmethod
	def _check_permission(ctx: discord.Message | QuasiContext, obj, scope: str):
		# Premission check
		if scope == 'channel' and not is_DM(obj):
			assert isinstance(ctx.author, discord.Member)
			p = get_guild_channel(obj).permissions_for(ctx.author)
			if not p.manage_channels:
				if isinstance(obj, discord.Thread):
					if ctx.author.id != obj.owner_id:
						raise PermissionDenied('thread')
				else:
					raise PermissionDenied('channel')
		elif scope == 'guild':
			assert isinstance(ctx.author, discord.Member)
			p = ctx.author.guild_permissions
			if not p.manage_guild:
				raise PermissionDenied('guild')

	async def _has_permission(self, var_or_scope: calcs.Var | Scope, user: discord.Member | discord.User) -> bool:
		if isinstance(var_or_scope, calcs.Var):
			scope = var_or_scope.scope
		else:
			scope = var_or_scope

		match scope:
			case UserScope():
				return scope.id == user.id
			case ChannelScope():
				assert isinstance(user, discord.Member)
				p = (await discord.utils.get_or_fetch(self.bot, 'channel', scope.id)).permissions_for(user)
				return p.manage_channels
			case GuildScope():
				assert isinstance(user, discord.Member)
				return user.guild_permissions.manage_guild
			case _:
				return False

	@staticmethod
	def _scope_to_readable(obj, scope: str) -> str:
		if scope == 'channel' and isinstance(obj, discord.Thread):
			return 'thread'
		return scope

	@staticmethod
	def _scope_option_process(ctx: discord.ApplicationContext, scope_option: str):
		channel = ctx.channel
		if scope_option == 'user':
			return 'user', ctx.author
		elif scope_option == 'this':
			return 'channel', channel
		elif scope_option == 'channel':
			return 'channel', get_guild_channel(channel)
		else:
			if is_DM(channel):
				raise NotInGuildError()
			return 'guild', channel.guild

	@discord.slash_command(
		description = 'Declare your own variable (no side-effects)',
		options = [
			discord.Option(str,
				name = 'name',
				description = 'Name of the variable'),
			discord.Option(str,
				name = 'value',
				description = 'Value of the variable (Default to integer 0)',
				default = '0'),
			discord.Option(str,
				name = 'scope',
				description = 'Where scope is this variable in (Default to "individual")',
				choices = [
					discord.OptionChoice('individual', 'user'),
					discord.OptionChoice('this thread (this channel if not in a thread)', 'this'),
					discord.OptionChoice('the channel (the outer channel if in a thread)', 'channel'),
					discord.OptionChoice('this guild', 'guild')
				],
				default = 'user'),
		]
	)
	async def declare(self, ctx, name, value, scope_option):
		scope, obj = self._scope_option_process(ctx, scope_option)

		n = await self._declare(ctx, obj, name, value)

		s = self.to_response(n, ctx.locale)
		await ctx.followup.send(self._trans(ctx, f'declare-success-{self._scope_to_readable(obj, scope)}', format = {'name': name, 'n': s}), ephemeral = (scope != 'user'))

	async def _declare(self, ctx: discord.Message | QuasiContext, obj, name: str, value: str, scope: str) -> Constant:
		self._check_permission(ctx, obj, scope)

		if not isinstance(ctx, discord.Message):
			await ctx.defer()

		if self._varsystem.exist_var(name, obj):
			raise RedeclareError(self._scope_to_readable(obj, scope), name)
		if not self.can_be_varname(name):
			raise InvalidVariableNameError(name)

		n, _ = await self._evaluate(ctx, value)

		# If another attempt to add var with the same name is done after we have done the checks, the below returns False.
		success = await self._varsystem.add_var(name, obj, n)
		if not success:
			raise RedeclareError(self._scope_to_readable(obj, scope), name)

		return n

	@discord.slash_command(
		description = 'Assign your variable with a value (no side-effects)',
		options = [
			discord.Option(str,
				name = 'name',
				description = 'Name of the variable'),
			discord.Option(str,
				name = 'value',
				description = 'Value of the variable'),
			discord.Option(str,
				name = 'scope',
				description = 'Where scope is this variable in (Default to "individual")',
				choices = [
					discord.OptionChoice('individual', 'user'),
					discord.OptionChoice('this thread (this channel if not in a thread)', 'this'),
					discord.OptionChoice('the channel (the outer channel if in a thread)', 'channel'),
					discord.OptionChoice('this guild', 'guild')
				],
				default = 'user'),
		]
	)
	async def assign(self, ctx, name, value, scope_option):
		scope, obj = self._scope_option_process(ctx, scope_option)

		n = await self._assign(ctx, obj, name, value, scope)

		...

	async def _assign(self, ctx: discord.Message | QuasiContext, obj, name: str, value: str, scope: str) -> bool:
		self._check_permission(ctx, obj, scope)

		if not self._varsystem.exist_var(name, obj):
			raise VarUndefinedError(self._scope_to_readable(obj, scope), name)

		if not isinstance(ctx, discord.Message):
			await ctx.defer()

		n, bookkeeping = await self._evaluate(ctx, value)
		var = self._varsystem.to_var(name, obj)

		return self._varsystem.update_var(var, n, bookkeeping.order)

	@discord.slash_command(
		description = 'Evaluate an expression (no side-effects)',
		options = [
			discord.Option(str,
				name = 'expression',
				description = 'Expression'),
		]
	)
	async def evaluate(self, ctx, expression):
		await ctx.defer()
		n, _ = await self._evaluate(ctx, expression)
		await ctx.followup.send(self.to_response(n, ctx.locale))

	async def _evaluate(self, ctx: discord.Message | QuasiContext, value: str) -> tuple[Constant, BookKeeping]:
		# @pre ctx is already deferred or ctx is message
		try:
			expr = self._parser.parse(value)
		except Exception as e:
			raise ParseError(e)

		try:
			bookkeeping = BookKeeping()
			mapping = self._varsystem.retrieve_mapping(ctx.author, ctx.channel, bookkeeping)
			n = await get_running_loop().run_in_executor(None, self._eval, expr, mapping, ctx)
		except Exception as e:
			raise CalculatorError(e)

		if n.is_lvalue:
			return n.content, bookkeeping
		return n, bookkeeping

	def _eval(self, expr: calcs.Expr, mapping, ctx):
		return expr.eval(mapping, bot = self.bot, ctx = ctx)

	async def _error_handle(self, ctx: QuasiContext | discord.Message, exception: _VarExtError):
		locale = self._pick_locale(ctx)

		match exception:
			case ParseError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'parse-error'),
					value = self._trans(locale, 'parse-error-value', format = {'type': type(exception.e).__name__, 'text': str(exception.e)}),
					**self._ephemeral(ctx)
				)
			case CalculatorError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'calcs-error'),
					value = self._trans(locale, 'calcs-error-value', format = {'type': type(exception.e).__name__, 'text': str(exception.e)}),
					**self._ephemeral(ctx)
				)
			case RedeclareError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'declare-failed-declared'),
					value = self._trans(locale, f'declare-failed-declared-{exception.scope}', format = {'name': exception.name}),
					**self._ephemeral(ctx)
				)
			case InvalidVariableNameError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'declare-failed-invalid'),
					value = self._trans(locale, 'declare-failed-invalid-value', format = {'name': exception.name}),
					**self._ephemeral(ctx)
				)
			case PermissionDenied():
				await send_error_embed(ctx,
					name = self._trans(locale, 'permission-denied'),
					value = self._trans(locale, f'permission-denied-{exception.scope}'),
					**self._ephemeral(ctx)
				)
			case NotInGuildError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'not-in-guild'),
					value = self._trans(locale, 'not-in-guild'),
					**self._ephemeral(ctx)
				)
			case VarUndefinedError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'var-undefined'),
					value = self._trans(locale, f'var-undefined-{exception.scope}', format = {'name': exception.name}),
					**self._ephemeral(ctx)
				)

	async def cog_command_error(self, ctx, exception: discord.ApplicationCommandError):
		match exception:
			case _VarExtError(): 
				await self._error_handle(ctx, exception)
			case _:
				# Propagate
				await super().cog_command_error(ctx, exception)

	@discord.Cog.listener()
	async def on_message(self, message):
		if not message.author.bot and message.content.startswith(_eval_prefix):
			expression = message.content[len(_eval_prefix):]
			try:
				n, _ = await self._evaluate(message, expression)
			except _VarExtError as e:
				await self._error_handle(message, e)
				return
			except Exception as e:
				await message.reply(f'```\n{e}```', **self._ephemeral(message))
				return

			await message.reply(self.to_response(n), self._pick_locale(message))

	@classmethod
	def to_response(cls, n: calcs.Constant, locale: Optional[str] = None) -> str:
		if n.is_number:
			prefix = self._trans(locale, 'number')
			return prefix + f' `{n}`'
		elif n.is_bool:
			prefix = self._trans(locale, 'boolean')
			if n.value:
				value = self._trans(locale, 'boolean-true')
			else:
				value = self._trans(locale, 'boolean-false')
			return f'{prefix} {value}'
		elif n.is_str:
			prefix = self._trans(locale, 'string')
			s = n.value
			if len(s) == 0:
				return prefix + ' ""'
			else:
				return prefix + f''' ``"{self.escape(s)}"``'''

	@classmethod
	def escape(cls, s):
		return cls._backticks.sub('`' + EmptyCharacter, s)

	def can_be_varname(self, name):
		return self._varname.fullmatch(name) and not name[0].isdigit() and not self._parser.is_op_symbol(name)

class _VarExtError(discord.ApplicationCommandError):
	pass

class ParseError(_VarExtError):
	def __init__(self, e):
		self.e = e

class CalculatorError(_VarExtError):
	def __init__(self, e):
		self.e = e

class RedeclareError(_VarExtError):
	def __init__(self, scope, name):
		self.scope = scope
		self.name = name

class InvalidVariableNameError(_VarExtError):
	def __init__(self, name):
		self.name = name

class PermissionDenied(_VarExtError):
	def __init__(self, scope):
		self.scope = scope

class NotInGuildError(_VarExtError):
	pass

class VarUndefinedError(_VarExtError):
	def __init__(self, scope, name):
		self.scope = scope
		self.name = name

def setup(bot):
	bot.add_cog(VarCommands(bot))
