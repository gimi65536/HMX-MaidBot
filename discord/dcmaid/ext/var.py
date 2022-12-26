# Let users handle variables for themselves...
from __future__ import annotations
import calcs
import discord
import discord.utils
import re
import sympy
from ..basebot import Bot
from ..basecog import BaseCog
from ..helper import set_help
from ..typing import ChannelType, GuildChannel, QuasiContext
from ..utils import *
from aiorwlock import RWLock
from asyncio import get_running_loop
from itertools import count
from typing import Literal, Optional, TypeAlias, TYPE_CHECKING

if TYPE_CHECKING:
	from pymongo.collection import Collection
	from typing import assert_type

config = generate_config(
	EXT_VAR_DB_BASED = {'default': False, 'cast': bool},
	EXT_VAR_DB_COLLECTION = {'default': 'var_system'},
)

class Scope:
	_id: int
	_is_user: bool = False
	_is_guild: bool = False
	_is_channel: bool = False

	def __init__(self, id_or_obj: int | discord.abc.Snowflake, /):
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
		self._order = next(self._count)

	@property
	def order(self):
		return self._order

class VariableSystem:
	def __init__(self, col: Optional[Collection] = None):
		self.col = col

		if col is not None:
			col.create_index([('scope_type', 1), ('scope_id', 1), ('name', 1)])

		self._managed_scopes: dict[int, Scope] = {} # id: Scope
		self._stored_value: dict[int, tuple[RWLock, dict[str, calcs.Constant]]] = {} # scope_id: (lock, {name: constant})
		self._update_record: dict[int, dict[str, int]] = {} # scope_id: {name: order}

	@staticmethod
	def to_var(name: str, obj) -> calcs.Var:
		match obj:
			case discord.User() | discord.Member():
				scope = UserScope(obj)
			case discord.Guild():
				scope = GuildScope(obj)
			case _:
				scope = ChannelScope(obj)

		return calcs.Var(name, scope)

	async def restore_info(self, bot: Bot):
		# Injure all names in SymPy
		for n in dir(sympy):
			if not n.startswith('_'):
				exec(f'{n}=sympy.{n}')

		if self.col is None:
			return

		info = self.col.aggregate([{
			'$group': {
				'_id': {'scope_type': '$scope_type', 'scope_id': '$scope_id'},
				'vars': {'$push': {'name': '$name', 'type': '$type', 'value': '$value'}}
			}
		}])
		for scope_info in info:
			scope_type, scope_id = scope_info['_id']['scope_type'], scope_info['_id']['scope_id']
			try:
				if scope_type == 'user':
					obj = await discord.utils.get_or_fetch(bot, 'user', scope_id)
					scope = UserScope(obj)
				elif scope_type == 'channel':
					obj = await discord.utils.get_or_fetch(bot, 'channel', scope_id)
					scope = ChannelScope(obj)
				elif scope_type == 'guild':
					obj = await discord.utils.get_or_fetch(bot, 'guild', scope_id)
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
						d[name] = calcs.StringConstant(value)
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

	async def add_var(self, name: str, obj: discord.User | discord.Member | discord.Guild | ChannelType, default: calcs.Constant = calcs.NumberConstant(sympy.Integer(0))) -> bool:
		match obj:
			case discord.User() | discord.Member():
				scope = self.add_scope(UserScope(obj))
			case discord.Guild():
				scope = self.add_scope(GuildScope(obj))
			case _:
				scope = self.add_scope(ChannelScope(obj))

		lock, d = self._stored_value[scope.id]

		with lock.writer:
			if name in self._stored_value[scope.id][1]:
				# raise ValueError(f'Variable {name} has been declared before!')
				return False

			d[name] = default
			self._update_record[scope.id][name] = 0

			if self.col is not None:
				self.col.insert_one(self.scope_to_document(scope) | {'name': name} | self.constant_to_document(default))

			return True

	def exist_var(self, name: str, obj: discord.User | discord.Member | discord.Guild | ChannelType) -> bool:
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

		if is_DM(channel):
			# channel scope
			scopes.append(self.add_scope(ChannelScope(channel)))
		elif is_not_DM(channel):
			# channel scope
			scopes.append(self.add_scope(ChannelScope(get_guild_channel(channel))))
			# guild scope
			scopes.append(self.add_scope(GuildScope(channel.guild)))

		for scope in scopes:
			d: dict[str, calcs.Constant]
			lock, d = self._stored_value[scope.id]
			async with lock.reader:
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
		# Methods in VarSystem do not restrict permissions.
		# If the bookkeeping is an original dict, the update is forcely done, or the BookKeeping.order is taken into account.
		table: dict[int, list[calcs.Var]] = {}
		for var in bookkeeping:
			if var.scope.id not in table:
				table[var.scope.id] = []
			table[var.scope.id].append(var)

		result: dict[calcs.Var, bool] = {}
		for scope_id, vars in table.items():
			# Not exists
			if scope_id not in self._stored_value:
				for var in vars:
					result[var] = False
				continue

			lock, d = self._stored_value[scope_id]
			r = self._update_record[scope_id]
			async with lock.writer:
				for var in vars:
					name = var.name
					if isinstance(bookkeeping, BookKeeping) and r[name] >= bookkeeping.order:
						result[var] = False
						continue
					if name not in d:
						# The variable is deleted
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

	async def delete_var(self, var: calcs.Var) -> bool:
		result = await self.bulk_delete([var])
		return result[var]

	async def bulk_delete(self, var_list: list[calcs.Var]) -> dict[calcs.Var, bool]:
		# Methods in VarSystem do not restrict permissions.
		# Scopes are never deleted.
		table: dict[int, list[calcs.Var]] = {}
		for var in var_list:
			if var.scope.id not in table:
				table[var.scope.id] = []
			table[var.scope.id].append(var)

		result: dict[calcs.Var, bool] = {}
		for scope_id, vars in table.items():
			# Not exists
			if scope_id not in self._stored_value:
				for var in vars:
					result[var] = False
				continue

			lock, d = self._stored_value[scope_id]
			r = self._update_record[scope_id]
			async with lock.writer:
				for var in vars:
					name = var.name
					if name not in d:
						# The variable is deleted
						result[var] = False
						continue
					result[var] = True

					d.pop(name)
					r.pop(name)

					if self.col is not None:
						self.col.delete_one({'scope_id': scope_id, 'name': name})

		return result

	@staticmethod
	def scope_to_document(scope: Scope):
		if scope.is_user_scope:
			return {'scope_id': scope.id, 'scope_type': 'user'}
		elif scope.is_guild_scope:
			return {'scope_id': scope.id, 'scope_type': 'guild'}
		elif scope.is_channel_scope:
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

	def _cast_scope(self, var: calcs.Var, bot: Bot, ctx: discord.Message | QuasiContext):
		raise NotImplementedError

class ToThreadOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if not isinstance(ctx.channel, discord.Thread):
			raise ValueError('Not in thread')
		var.scope = ChannelScope(ctx.channel)

class ToChannelOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if is_DM(ctx.channel):
			var.scope = ChannelScope(ctx.channel)
		else:
			if TYPE_CHECKING:
				assert isinstance(ctx.channel, GuildChannel)

			var.scope = ChannelScope(get_guild_channel(ctx.channel))

class ToGuildOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		if is_DM(ctx.channel):
			raise ValueError('Not in guild')

		if TYPE_CHECKING:
			assert isinstance(ctx.channel, GuildChannel)

		var.scope = GuildScope(ctx.channel.guild)

class ToIndividualOperator(_ChangeScopeOperator):
	def _cast_scope(self, var, bot, ctx):
		author = get_author(ctx)
		if TYPE_CHECKING:
			assert author is not None

		var.scope = UserScope(author)

_eval_prefix = '=$'

scope_option = discord.Option(str,
	name = 'scope',
	description = 'Where scope is this variable in (Default to "individual")',
	choices = [
		discord.OptionChoice('individual', 'user'),
		discord.OptionChoice('here', 'this'),
		discord.OptionChoice('channel', 'channel'),
		discord.OptionChoice('guild', 'guild')
	],
	default = 'user')

ScopeOptionLiteral: TypeAlias = Literal['user', 'this', 'channel', 'guild']
ScopeLiteral: TypeAlias = Literal['user', 'channel', 'guild']

class VarCommands(BaseCog, name = 'Var'):
	_backticks = re.compile('`(?=`)|`$')
	_varname = re.compile(r'\w+')

	def __init__(self, bot: Bot):
		super().__init__(bot)
		self._parser: calcs.Parser = calcs.give_basic_parser() # ad-hoc
		self._var_col = bot.db[config['EXT_VAR_DB_COLLECTION']] if config['EXT_VAR_DB_BASED'] else None
		self._varsystem: VariableSystem = VariableSystem(self._var_col)

	@discord.Cog.listener()
	async def on_ready(self):
		await self._varsystem.restore_info(self.bot)

	@staticmethod
	def _check_permission(ctx: discord.Message | QuasiContext, obj, scope: ScopeLiteral):
		user = get_author(ctx)

		# Premission check
		if scope == 'channel' and is_not_DM(obj):
			assert isinstance(user, discord.Member)
			p = get_guild_channel(obj).permissions_for(user)
			if not p.manage_channels:
				if isinstance(obj, discord.Thread):
					if user.id != obj.owner_id:
						raise PermissionDenied('thread')
				else:
					raise PermissionDenied('channel')
		elif scope == 'guild':
			assert isinstance(user, discord.Member)
			p = user.guild_permissions
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
	def _scope_option_process(ctx: discord.ApplicationContext, scope_option: ScopeOptionLiteral):
		channel = ctx.channel
		assert channel is not None

		if scope_option == 'user':
			return 'user', ctx.author
		elif scope_option == 'this':
			return 'channel', channel
		elif scope_option == 'channel':
			if channel is None:
				raise NotInGuildError()

			if is_not_DM(channel):
				return 'channel', get_guild_channel(channel)
			else:
				return 'channel', channel
		else:
			if TYPE_CHECKING:
				assert_type(scope_option, Literal['guild'])

			if channel is not None and is_not_DM(channel):
				return 'guild', channel.guild

			raise NotInGuildError()

	var_cmd_group = discord.SlashCommandGroup(
		name = "var",
		description = "Variable management"
	)
	set_help(var_cmd_group,
		'''
		These commands manages variable information.
		'''
	)

	@var_cmd_group.command(
		description = 'Declare a variable (no side-effects)',
		options = [
			discord.Option(str,
				name = 'name',
				description = 'Name of the variable'),
			discord.Option(str,
				name = 'value',
				description = 'Value of the variable (Default to integer 0)',
				default = '0'),
			scope_option,
		]
	)
	async def declare(self, ctx: discord.ApplicationContext, name: str, value: str, scope_option: ScopeOptionLiteral):
		'''
		`/{cmd_name} <name> <?value> <?scope>` declares a variable with a value in the scope.
		By default, value is 0 and scope is individual.
		'''
		scope, obj = self._scope_option_process(ctx, scope_option)

		n = await self._declare(ctx, obj, name, value, scope)

		s = self.to_response(n, ctx.locale)
		await ctx.followup.send(self._trans(ctx, f'declare-success-{self._scope_to_readable(obj, scope)}', format = {'name': name, 'n': s}), ephemeral = (scope != 'user'))

	async def _declare(self, ctx: discord.Message | QuasiContext, obj, name: str, value: str, scope: ScopeLiteral) -> calcs.Constant:
		self._check_permission(ctx, obj, scope)

		if self._varsystem.exist_var(name, obj):
			raise RedeclareError(self._scope_to_readable(obj, scope), name)
		if not self.can_be_varname(name):
			raise InvalidVariableNameError(name)

		if not isinstance(ctx, discord.Message):
			await ctx.response.defer()

		n, _ = await self._evaluate(ctx, value)

		# If another attempt to add var with the same name is done after we have done the checks, the below returns False.
		success = await self._varsystem.add_var(name, obj, n)
		if not success:
			raise RedeclareError(self._scope_to_readable(obj, scope), name, n)

		return n

	@var_cmd_group.command(
		description = 'Assign a variable with a value (no side-effects)',
		options = [
			discord.Option(str,
				name = 'name',
				description = 'Name of the variable'),
			discord.Option(str,
				name = 'value',
				description = 'Value of the variable'),
			scope_option,
			discord.Option(bool,
				name = 'declare',
				description = 'Declare the variable if the variable does not exist (Default to false)',
				default = False),
		]
	)
	async def assign(self, ctx: discord.ApplicationContext, name: str, value: str, scope_option: ScopeOptionLiteral, declare: bool):
		'''
		`/{cmd_name} <name> <value> <?scope> <?declare>` updates a variable with a value in the scope.
		By default, scope is individual and auto-declaration is disabled.
		'''
		scope, obj = self._scope_option_process(ctx, scope_option)

		n = await self._assign(ctx, obj, name, value, scope, declare)

		s = self.to_response(n, ctx.locale)
		await ctx.followup.send(self._trans(ctx, f'update-success-{self._scope_to_readable(obj, scope)}', format = {'name': name, 'n': s}), ephemeral = (scope != 'user'))

	async def _assign(self, ctx: discord.Message | QuasiContext, obj, name: str, value: str, scope: ScopeLiteral, declare: bool = False) -> calcs.Constant:
		if declare:
			try:
				n = await self._declare(ctx, obj, name, value, scope)
			except RedeclareError as e:
				if e.n is not None:
					# Some other process takes the lead to declare the variable...
					raise UpdateFailedError(self._scope_to_readable(obj, scope), name, e.n)
				else:
					# If declared, then continue to assign (the ctx has not deferred)
					pass
			# The other exceptions are propagated
			else:
				# The declaration completes
				return n

			# You get here if RedeclareError and e.n is None, and the permission checks are done.
		else:
			# If declare, the checks are done already. We only check if not declare.
			self._check_permission(ctx, obj, scope)

			if not self._varsystem.exist_var(name, obj):
				raise VarUndefinedError(self._scope_to_readable(obj, scope), name)

		# Below is the main parts of _assign

		if not isinstance(ctx, discord.Message):
			await ctx.response.defer()

		n, bookkeeping = await self._evaluate(ctx, value)
		var = self._varsystem.to_var(name, obj)

		success = self._varsystem.update_var(var, n, bookkeeping.order)
		if not success:
			raise UpdateFailedError(self._scope_to_readable(obj, scope), name, n)

		return n

	@var_cmd_group.command(
		description = 'Remove a variable',
		options = [
			discord.Option(str,
				name = 'name',
				description = 'Name of the variable'),
			scope_option,
		]
	)
	async def remove(self, ctx: discord.ApplicationContext, name: str, scope_option: ScopeOptionLiteral):
		'''
		`/{cmd_name} <name> <?scope>` removes a variable in the scope.
		By default, scope is individual.
		'''
		scope, obj = self._scope_option_process(ctx, scope_option)

		await self._remove(ctx, obj, name, scope)
		await ctx.send_response(self._trans(ctx, f'remove-success-{self._scope_to_readable(obj, scope)}', format = {'name': name}), ephemeral = (scope != 'user'))

	async def _remove(self, ctx: discord.Message | QuasiContext, obj, name: str, scope: ScopeLiteral):
		self._check_permission(ctx, obj, scope)

		var = self._varsystem.to_var(name, obj)
		success = self._varsystem.delete_var(var)
		if not success:
			raise RemoveVariableFailedError(self._scope_to_readable(obj, scope), name)

	@discord.slash_command(
		description = 'Evaluate an expression (no side-effects)',
		options = [
			discord.Option(str,
				name = 'expression',
				description = 'Expression'),
		]
	)
	async def evaluate(self, ctx: discord.ApplicationContext, expression: str):
		'''
		`/{cmd_name} <expression>` evaluates the expression.
		'''
		await ctx.defer()
		n, _ = await self._evaluate(ctx, expression)
		await ctx.followup.send(self.to_response(n, ctx.locale))

	async def _evaluate(self, ctx: discord.Message | QuasiContext, value: str) -> tuple[calcs.Constant, BookKeeping]:
		# @pre ctx is already deferred or ctx is message
		try:
			expr = self._parser.parse(value)
		except Exception as e:
			raise ParseError(e)

		user = get_author(ctx)
		assert user is not None
		assert ctx.channel is not None

		try:
			bookkeeping = BookKeeping()
			mapping = await self._varsystem.retrieve_mapping(user, ctx.channel, bookkeeping)
			n = await get_running_loop().run_in_executor(None, self._eval, expr, mapping, ctx)
		except Exception as e:
			raise CalculatorError(e)

		if n.is_lvalue:
			if TYPE_CHECKING:
				assert isinstance(n, calcs.LValue)
			return n.content, bookkeeping
		else:
			if TYPE_CHECKING:
				assert isinstance(n, calcs.Constant)
			return n, bookkeeping

	def _eval(self, expr: calcs.TreeNodeType, mapping: dict[calcs.Var, calcs.LValue], ctx: discord.Message | QuasiContext):
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
			case UpdateFailedError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'update-failed'),
					value = self._trans(locale, f'update-failed-{exception.scope}', format = {'name': exception.name, 'n': exception.n}),
					**self._ephemeral(ctx)
				)
			case RemoveVariableFailedError():
				await send_error_embed(ctx,
					name = self._trans(locale, 'remove-failed'),
					value = self._trans(locale, f'remove-failed-{exception.scope}', format = {'name': exception.name}),
					**self._ephemeral(ctx)
				)

	async def cog_command_error(self, ctx, exception):
		match exception:
			case _VarExtError(): 
				await self._error_handle(ctx, exception)
			case _:
				# Propagate
				await super().cog_command_error(ctx, exception)

	@discord.Cog.listener()
	async def on_message(self, message: discord.Message):
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

			await message.reply(self.to_response(n, self._pick_locale(message)))

	@classmethod
	def to_response(cls, n: calcs.Constant, locale: Optional[str] = None) -> str:
		if n.is_number:
			prefix = cls._trans(locale, 'number')
			return prefix + f' `{n}`'
		elif n.is_bool:
			prefix = cls._trans(locale, 'boolean')
			if n.value:
				value = cls._trans(locale, 'boolean-true')
			else:
				value = cls._trans(locale, 'boolean-false')
			return f'{prefix} {value}'
		elif n.is_str:
			prefix = cls._trans(locale, 'string')
			s = n.value
			if len(s) == 0:
				return prefix + ' ""'
			else:
				return prefix + f''' ``"{cls.escape(s)}"``'''
		else:
			raise ValueError('Unknown to_response error')

	@classmethod
	def escape(cls, s: str):
		return cls._backticks.sub('`' + EmptyCharacter, s)

	def can_be_varname(self, name: str):
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
	def __init__(self, scope, name, n: Optional[calcs.Constant] = None):
		# None n indicates the value has not been evaluated
		self.scope = scope
		self.name = name
		self.n = n

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

class UpdateFailedError(_VarExtError):
	def __init__(self, scope, name, n):
		self.scope = scope
		self.name = name
		self.n = n

class RemoveVariableFailedError(_VarExtError):
	def __init__(self, scope, name):
		self.scope = scope
		self.name = name

def setup(bot):
	bot.add_cog(VarCommands(bot))
