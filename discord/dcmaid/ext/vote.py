import discord
import uuid
from ..basebot import Bot
from ..basecog import BaseCog, MaidMixin, RandomMixin
from ..utils import *
from ..views import YesNoView
from asyncio import get_running_loop, Lock, sleep, Task
from collections import Counter
from dataclasses import dataclass
from decouple import config
from datetime import datetime, timedelta, timezone
from simple_parsers.string_argument_parser import StringArgumentParser
from types import MappingProxyType
from typing import (
	Awaitable,
	Counter as CounterType,
	Dict,
	Generic,
	List,
	Mapping,
	MutableMapping,
	Optional,
	Set,
	Tuple,
	Type,
	TypeVar
)

time_units = [
	('second', 's'),
	('minute', 'm'),
	('hour', 'h'),
	('day', 'd'),
	('week', 'w'),
	#('forever', 'f') # It is hard to handle a forever poll... though forever polls are useful.
]
time_units_options = [discord.Option(name, value) for name, value in time_units]

def period_to_delta(period: int, period_unit) -> Optional[timedelta]:
	match period_unit:
		case 's':
			time_delta = timedelta(seconds = period)
		case 'm':
			time_delta = timedelta(minites = period)
		case 'h':
			time_delta = timedelta(hours = period)
		case 'd':
			time_delta = timedelta(days = period)
		case 'w':
			time_delta = timedelta(weeks = period)
		case 'f':
			time_delta = None

	return time_delta

# This is just a data type. We don't do much logic in this class.
# It is recommended to create a poll with hold system instead of direct creation.
# _vote_* dictionaries are designed to be manipulated by hold systems.
class BasePoll:
	author: discord.Member
	channel: discord.abc.Messageable
	title: str
	options: List[str]
	_option_set: Set[str] # Not in db
	vote_receive: Mapping[str, CounterType[discord.Member]] # Not in db
	vote_casted: Mapping[discord.Member, CounterType[str]]
	_vote_receive: MutableMapping[str, CounterType[discord.Member]] # Not in db
	_vote_casted: MutableMapping[discord.Member, CounterType[str]]
	uuid: uuid.UUID
	msg_id: Optional[int] = None # Inserted by the Cog
	processed_order: int # Not in db. Used by the Cog to refresh information correctly.
	mutex: Lock # Not in db, of course

	def __init__(self, author: discord.Member, channel: discord.abc.Messageable, title: str, options: List[str], period: int, period_unit):
		if period <= 0:
			raise NonPositivePeriodError(period)

		time_delta: Optional[timedelta] = period_to_delta(period, period_unit)
		self._time = time_delta

		self.author = author
		self.channel = channel
		self.title = title

		_o = {o: None for o in options}
		self.options = list(_o.keys())
		self._option_set = set(_o.keys())

		self._vote_receive = {o: Counter() for o in self.options}
		self._vote_casted = {}
		self.vote_receive = {o: MappingProxyType(self._vote_receive[o]) for o in self.options}
		self.vote_casted = {}

		self.uuid = uuid.uuid4()
		self.processed_order = 0
		self.mutex = Lock()

	def has_user(self, member: discord.Member):
		return member in self._vote_casted

	def add_user(self, member: discord.Member):
		if member in self._vote_casted:
			return

		self._vote_casted[member] = Counter({o: 0 for o in self.options})
		self.vote_casted[member] = MappingProxyType(self._vote_casted[member])

	@property
	def until(self) -> Optional[datetime]:
		if hasattr(self, '_until'):
			return self._until

		if self._time is not None:
			self._until = datetime.now(timezone.utc) + self._time
		else:
			self._until = None
		return self._until

	def put_in_system(self, system):
		# To ensure the poll is only handled by one system.
		if not hasattr(self, '_system'):
			self._system = system
		else:
			if self._system is not system:
				raise AttributeError("This poll has already belonged to a system.")

	def connect_to_msg(self, msg: discord.Message):
		self.msg_id = msg.id

	def get_votes_per_option(self) -> Dict[str, int]:
		# This method is unstable when the mutex is locked and the caller doesn't hold it.
		result = {}
		for o, d in self._vote_receive.items():
			result[o] = d.total()
		return result

	def __hash__(self):
		return hash(self.uuid)

	def __eq__(self, other):
		return self.uuid == other.uuid

class Poll(BasePoll):
	#until: Optional[datetime]
	realtime: bool
	show_name_voting: bool
	show_name_result: bool
	min_votes: int
	max_votes: int

	def __init__(self,
		author: discord.User,
		channel: discord.abc.Messageable,
		title: str,
		options: List[str],
		period: int,
		period_unit,
		realtime: bool,
		show_name: bool,
		show_name_voting: Optional[bool],
		show_name_result: Optional[bool],
		num_votes: int,
		min_votes: Optional[int],
		max_votes: Optional[int]):

		length = len(options)
		if length == 0:
			raise EmptyChoiceError()

		super().__init__(author, channel, title, options, period, period_unit)

		# Checks
		self.realtime = realtime

		if show_name_voting is None:
			self.show_name_voting = show_name
		else:
			self.show_name_voting = show_name_voting

		if show_name_result is None:
			self.show_name_result = show_name
		else:
			self.show_name_result = show_name_result

		if min_votes is None:
			self.min_votes = num_votes
		else:
			self.min_votes = min_votes

		if max_votes is None:
			self.max_votes = num_votes
		else:
			self.max_votes = max_votes

		if self.min_votes > self.max_votes:
			raise MinMaxError(self.min_votes, self.max_votes)
		if self.min_votes < 0:
			self.min_votes = 0
		if self.max_votes < 0:
			self.max_votes = 0
		if self.min_votes == 0 and self.max_votes == 0:
			raise ZeroVoteError()

		if self.min_votes > length:
			self.min_votes = length
		if self.max_votes > length:
			self.max_votes = length

@dataclass(init = True, repr = True, eq = False, frozen = True)
class Event:
	poll: BasePoll
	member: discord.Member
	option: str
	modification: Tuple[int, int] # (From, To)
	processed_order: int

T = TypeVar('T', bound = BasePoll)

class BaseHoldSystem(Generic[T]):
	'''
	Use db column to restore or not...
	'''
	def __init__(self, name: str, type: Type[T], col = None):
		self._on_process: Dict[uuid.UUID, Tuple[T, Task]] = {}
		self.name = name
		self.type = type
		self.col = col
		self._restore_poll = []

		if col is not None:
			col.create_index({'uuid': 1})
			# Restore poll from database, but this class does not register them
			# since this class has no knowledge about timeout awaitable
			NotImplemented

	def restore_poll(self):
		# This method should be called by cogs right after the hold system is created
		return iter(self._restore_poll)

	def _contain(self, poll_or_u: BasePoll | uuid.UUID):
		if isinstance(poll_or_u, BasePoll):
			u = poll_or_u.uuid
		else:
			u = poll_or_u

		return u in self._on_process

	def retrieve(self, u: uuid.UUID) -> Optional[T]:
		if u not in self._on_process:
			return None

		return self._on_process.get(u)[0]

	async def register(self, poll: T, awaitable: Awaitable):
		# awaitable will be awaited within the poll mutex
		async with poll.mutex:
			if self._contain(poll):
				return

			poll.put_in_system(self)

			loop = get_running_loop()
			task = loop.create_task(self.wait_for_timeout(poll, awaitable))
			self._on_process[poll.uuid] = (poll, task)

			if self.col is not None:
				NotImplemented

	async def cancel(self, poll_or_u: T | uuid.UUID) -> bool:
		if isinstance(poll_or_u, BasePoll):
			u = poll_or_u.uuid
		else:
			u = poll_or_u

		t = self._on_process.get(u, None)
		if t is None:
			return
		poll, task = t

		async with poll.mutex:
			if not self._contain(poll):
				return False # Not canceled by this method

			self._on_process.pop(u)
			poll.processed_order += 1 # To prevent late information update after the poll is canceled
			task.cancel()

			if self.col is not None:
				NotImplemented

			return True # Canceled by this method

	async def wait_for_timeout(self, poll: T, awaitable: Awaitable):
		await discord.utils.sleep_until(poll.until)
		async with poll.mutex:
			if not self._contain(poll):
				return

			self._on_process.pop(poll.uuid)
			poll.processed_order += 1 # To prevent late information update after due

			if self.col is not None:
				NotImplemented

			# awaitable is called after the processed order increased
			await awaitable

	async def add_votes(self, poll: T, member: discord.Member, options: List[str] | Counter[str]) -> Optional[List[Event]]:
		if not self._contain(poll):
			# Happen if timeout
			return None
		options = self._process_options(options)
		return await self._add_votes(poll, member, options)

	async def replace_votes(self, poll: T, member: discord.Member, options: List[str] | Counter[str]) -> Optional[List[Event]]:
		if not self._contain(poll):
			# Happen if timeout
			return None
		options = self._process_options(options)
		return await self._replace_votes(poll, member, options)

	async def remove_votes(self, poll: T, member: discord.Member, options: Optional[List[str] | Counter[str]] = None) -> Optional[List[Event]]:
		if not self._contain(poll):
			# Happen if timeout
			return None
		options = self._process_options(options)
		return await self._remove_votes(poll, member, options)

	async def add_votes_by_uuid(self, uuid: uuid.UUID, member: discord.Member, options: List[str] | Counter[str]) -> Optional[List[Event]]:
		if not self._contain(poll):
			# Happen if timeout
			return None
		options = self._process_options(options)
		return await self._add_votes(self.retrieve(uuid), member, options)

	async def replace_votes_by_uuid(self, uuid: uuid.UUID, member: discord.Member, options: List[str] | Counter[str]) -> Optional[List[Event]]:
		if not self._contain(poll):
			# Happen if timeout
			return None
		options = self._process_options(options)
		return await self._replace_votes(self.retrieve(uuid), member, options)

	async def remove_votes_by_uuid(self, uuid: uuid.UUID, member: discord.Member, options: Optional[List[str] | Counter[str]] = None) -> Optional[List[Event]]:
		if not self._contain(poll):
			# Happen if timeout
			return None
		options = self._process_options(options)
		return await self._remove_votes(self.retrieve(uuid), member, options)

	# This implementation is default behaviors. Feel free to override this method.
	# None options are only used in remove
	def _process_options(self, options: Optional[List[str] | Counter[str]]) -> Optional[Counter[str]]:
		if options is None:
			return None

		return Counter(options)

	async def _add_votes(self, poll: T, member: discord.Member, options: Counter[str]) -> Optional[List[Event]]:
		raise NotImplementedError

	async def _replace_votes(self, poll: T, member: discord.Member, options: Counter[str]) -> Optional[List[Event]]:
		raise NotImplementedError

	async def _remove_votes(self, poll: T, member: discord.Member, options: Optional[Counter[str]]) -> Optional[List[Event]]:
		raise NotImplementedError

class PollHoldSystem(HoldSystem[Poll]):
	def __init__(self, col = None):
		super().__init__('poll', Poll, col)

	def _process_options(self, options: Optional[List[str] | Counter[str]]) -> Optional[Counter[str]]:
		if options is None:
			return None

		if isinstance(options, Counter):
			return Counter(set(options.elements()))
		else:
			return Counter(set(options))

	async def _add_votes(self, poll: Poll, member: discord.Member, options: Counter[str]) -> Optional[List[Event]]:
		events = []
		async with poll.mutex:
			if not self._contain(poll):
				# Happen if timeout
				return

			poll.add_user(member)
			processed_order = poll.processed_order + 1

			for option, count in options.items():
				if count <= 0:
					continue
				if option not in poll._option_set:
					continue

				if poll._vote_casted[member][option] == 0:
					# Event
					poll._vote_casted[member][option] = 1
					poll._vote_receive[option][member] = 1
					events.append(Event(poll, member, option, (0, 1), processed_order))

			if len(events) > 0:
				# Update processed_order only if necessary to prevent suppressed update
				poll.processed_order = processed_order

			if self.col is not None:
				NotImplemented

		return events

	async def _replace_votes(self, poll: Poll, member: discord.Member, options: Counter[str]) -> Optional[List[Event]]:
		events = []
		async with poll.mutex:
			if not self._contain(poll):
				# Happen if timeout
				return

			poll.add_user(member)
			processed_order = poll.processed_order + 1

			for option, count in options.items():
				if count < 0:
					continue
				if option not in poll._option_set:
					continue

				if count > 0 and poll._vote_casted[member][option] == 0:
					# Event
					poll._vote_casted[member][option] = 1
					poll._vote_receive[option][member] = 1
					events.append(Event(poll, member, option, (0, 1), processed_order))
				elif count == 0 and poll._vote_casted[member][option] == 1:
					# Event
					poll._vote_casted[member][option] = 0
					poll._vote_receive[option][member] = 0
					events.append(Event(poll, member, option, (1, 0), processed_order))

			if len(events) > 0:
				# Update processed_order only if necessary to prevent suppressed update
				poll.processed_order = processed_order

			if self.col is not None:
				NotImplemented

		return events

	async def _remove_votes(self, poll: Poll, member: discord.Member, options: Optional[Counter[str]]) -> Optional[List[Event]]:
		events = []
		async with poll.mutex:
			if not self._contain(poll):
				# Happen if timeout
				return

			poll.add_user(member)
			processed_order = poll.processed_order + 1

			if options is None:
				for vote in list(poll._vote_casted[member].elements()):
					# Event
					poll._vote_casted[member][vote] = 0
					poll._vote_receive[vote][member] = 0
					events.append(Event(poll, member, vote, (1, 0), processed_order))
			else:
				for option, count in options.items():
					if count <= 0:
						continue
					if option not in poll._option_set:
						continue

					if poll._vote_casted[member][option] == 1:
						# Event
						poll._vote_casted[member][option] = 0
						poll._vote_receive[option][member] = 0
						events.append(Event(poll, member, option, (1, 0), processed_order))

			if len(events) > 0:
				# Update processed_order only if necessary to prevent suppressed update
				poll.processed_order = processed_order

			if self.col is not None:
				NotImplemented

		return events

'''
class BetHoldSystem(HoldSystem[Bet]):
	def __init__(self, col = None):
		super().__init__('bet', Bet, col)

	...
'''

class VoteOptionView(discord.View):
	# Presistent during the lifetime of the poll
	prefix: str = config('VOTE_CUSTOM_PREFIX', default = 'HMX-vote-cog')

	def __init__(
		self,
		poll,
		vote_label,
		vote_callback,
		lookup_label,
		lookup_callback,
		early_label,
		early_callback,
		cancel_label,
		cancel_callback
	):
		super().__init__(timeout = None)

		vote_button = disord.Button(
			callback = vote_callback,
			label = vote_label,
			style = discord.ButtonStyle.primary,
			custom_id = f'{self.prefix}:vote:{poll.uuid}',
			emoji = '\u2611', #'\U0001F5F9'
			row = 0
		)
		lookup_button = disord.Button(
			callback = vote_callback,
			label = lookup_label,
			style = discord.ButtonStyle.secondary,
			custom_id = f'{self.prefix}:lookup:{poll.uuid}',
			emoji = '\U0001F50E',
			row = 0
		)
		early_button = disord.Button(
			callback = early_callback,
			label = early_label,
			style = discord.ButtonStyle.secondary,
			custom_id = f'{self.prefix}:early:{poll.uuid}',
			emoji = '\u23E9',
			row = 0
		)
		cancel_button = disord.Button(
			callback = cancel_callback,
			label = cancel_label,
			style = discord.ButtonStyle.danger,
			custom_id = f'{self.prefix}:cancel:{poll.uuid}',
			emoji = '\u274C',
			row = 0
		)

		self.add_item(vote_button)
		self.add_item(lookup_button)
		self.add_item(early_button)
		self.add_item(cancel_button)

class VoteView(discord.View):
	def __init__(self, poll, select_callback, empty_label, empty_callback):
		super().__init__(timeout = 0)

		options = [discord.SelectOption(label = o) for o in poll.options]

		select = discord.Select(
			callback = select_callback,
			options = options,
			min_values = poll.min_votes,
			max_values = poll.max_votes,
			row = 0
		)
		button = discord.Button(
			callback = empty_callback,
			label = empty_label,
			style = discord.ButtonStyle.danger,
			row = 1
		)

		self.add_item(select)
		self.add_item(button)

class VoteController(Generic[T]):
	'''
	First-layer actions:
	These actions are designed to be invoked when users click buttons attached to a poll
	and need to "send" an ephermal response.
	vote_action acts as a basic response, so it also provides an "edit" variation.
	'''
	@classmethod
	def vote_action(cls, cog: 'VoteCommands', system: HoldSystem[T], poll: T, edit = False):
		raise NotImplementedError

	@classmethod
	def lookup_action(cls, cog: 'VoteCommands', system: HoldSystem[T], poll: T):
		raise NotImplementedError

	@classmethod
	def early_action(cls, cog: 'VoteCommands', system: HoldSystem[T], poll: T):
		raise NotImplementedError

	@classmethod
	def cancel_action(cls, cog: 'VoteCommands', system: HoldSystem[T], poll: T):
		raise NotImplementedError

	'''
	Second-layer actions:
	These actions are designed to be invoked when users click buttons attached to an action
	in the first-layer and need to "edit" the ephermal responses.
	Of course, if an error occurs, these actions are allowed to "send" ephermal error messages.
	'''

	@classmethod
	def select_action(cls, cog: 'VoteCommands', system: HoldSystem[T], poll: T):
		raise NotImplementedError

	@classmethod
	def empty_action(cls, cog: 'VoteCommands', system: HoldSystem[T], poll: T):
		raise NotImplementedError

class PollController(VoteController[Poll]):
	@classmethod
	def vote_action(cls, cog, system, poll, edit = False):
		async def f(button, interaction):
			member = interaction.user
			assert member is not None

			async with poll.mutex:
				if not poll.has_user(member):
					poll.add_user(member)
				has_voted = list(poll.vote_casted[member].elements())

			content = ''
			if len(has_voted) == 0:
				content = cog._trans(interaction, 'not-vote-yet', format = {'title': poll.title})
			else:
				has_voted = [f'`{s}`' for s in has_voted]
				content = f'{cog._trans(interaction, 'has-vote', format = {'title': poll.title})}\n{' '.join(has_voted)}'

			if edit:
				await interaction.response.edit_message(
					content = content,
					view = VoteView(
						poll = poll,
						select_callback = cls.select_action(cog, system, poll),
						empty_label = cog._trans(interaction, 'empty'),
						empty_callback = cls.empty_action(cog, system, poll)
					)
				)
			else:
				await interaction.response.send_message(
					content = content,
					view = VoteView(
						poll = poll,
						select_callback = cls.select_action(cog, system, poll),
						empty_label = cog._trans(interaction, 'empty'),
						empty_callback = cls.empty_action(cog, system, poll)
					),
					ephemeral = True
				)

		return f

	@classmethod
	def lookup_action(cls, cog, system, poll):
		async def f(button, interaction):
			member = interaction.user
			assert member is not None

			async with poll.mutex:
				if not poll.has_user(member):
					poll.add_user(member)
				has_voted = list(poll.vote_casted[member].elements())

			content = ''
			if len(has_voted) == 0:
				content = cog._trans(interaction, 'not-vote-yet', format = {'title': poll.title})
			else:
				has_voted = [f'`{s}`' for s in has_voted]
				content = f'{cog._trans(interaction, 'has-vote', format = {'title': poll.title})}\n{' '.join(has_voted)}'

			await interaction.response.send_message(content = content, ephemeral = True)

		return f

	@classmethod
	def early_action(cls, cog, system, poll):
		async def f(button, interaction):
			member = interaction.user
			assert member is not None

			if poll.author != member:
				await send_error_embed(interaction,
					name = self._trans(interaction, 'early-permission-denied'),
					value = self._trans(interaction, 'early-permission-denied-value'),
					ephemeral = True
				)
			else:
				await interaction.response.send_message(
					content = cog._trans(interaction, 'early-check', format = {'title': poll.title}),
					view = YesNoView(
						yes_callback = cls.ensured_early_action(cog, system, poll)
					),
					ephemeral = True
				)

		return f

	@classmethod
	def ensured_early_action(cls, cog, system, poll):
		async def f(button, interaction):
			await interaction.response.edit_message(
				content = cog._trans(interaction, 'early-done'),
				view = None
			)

			member = interaction.user
			assert member is not None

			if poll.author != member:
				# This should not be triggered
				return # Silence
			else:
				result = await system.cancel(poll)
				if result:
					async with poll.mutex:
						await cog._timeout_process(poll)

		return f

	@classmethod
	def cancel_action(cls, cog, system, poll):
		async def f(button, interaction):
			member = interaction.user
			assert member is not None

			if poll.author != member or not poll.channel.permissions_for(member).manage_messages:
				await send_error_embed(interaction,
					name = self._trans(interaction, 'cancel-permission-denied'),
					value = self._trans(interaction, 'cancel-permission-denied-value'),
					ephemeral = True
				)
			else:
				await interaction.response.send_message(
					content = cog._trans(interaction, 'cancel-check', format = {'title': poll.title}),
					view = YesNoView(
						yes_callback = cls.ensured_cancel_action(cog, system, poll)
					),
					ephemeral = True
				)

		return f

	@classmethod
	def ensured_cancel_action(cls, cog, system, poll):
		async def f(button, interaction):
			await interaction.response.edit_message(
				content = cog._trans(interaction, 'cancel-done'),
				view = None
			)

			member = interaction.user
			assert member is not None

			if poll.author != member:
				# This should not be triggered
				return # Silence
			else:
				result = await system.cancel(poll)
				if result: # This cancellation is handled by this method
					embed = discord.Embed(
						title = poll.title,
						description = cog._trans(interaction, 'canceled-poll'),
						color = discord.Color.grey
					)
					await poll.message.edit(content = "", embed = embed, view = None)

		return f

	@classmethod
	def select_action(cls, cog, system, poll):
		async def f(select, interaction):
			# This is a server-side check
			# Do nothing
			l = len(select.value)
			if l < poll.min_votes or l > poll.max_votes:
				await interaction.defer()
				return

			options = '\n'.join(select.value)
			content = f'```{options}```'
			await interaction.response.edit_message(
				content = content,
				view = YesNoView(
					yes_callback = cls.ensured_select_action(cog, system, poll, select.value),
					no_callback = cls.vote_action(cog, system, poll, edit = True)
				)
			)

		return f

	@classmethod
	def ensured_select_action(cls, cog, system, poll, options):
		async def f(button, interaction):
			await interaction.response.edit_message(
				content = '......',
				view = None
			)
			member = interaction.user
			assert member is not None

			result = await system.replace_votes(poll, interaction.user, options)
			if result is None:
				# Due
				await interaction.message.edit(content = cog._trans(interaction, 'vote-failed'))
			else:
				await interaction.message.edit(content = cog._trans(interaction, 'vote-success'))
				if len(result) > 0:
					peek: Event = result[0]
					async with poll.mutex:
						if poll.processed_order == peek.processed_order:
							await cog._render(poll)

	@classmethod
	def empty_action(cls, cog, system, poll):
		async def f(button, interaction):
			member = interaction.user
			assert member is not None

			await interaction.response.edit_message(
				content = cog._trans(interaction, 'empty-check'),
				view = YesNoView(
					yes_callback = cls.ensured_empty_action(cog, system, poll),
					no_callback = cls.vote_action(cog, system, poll, edit = True)
				)
			)

		return f

	@classmethod
	def ensured_empty_action(cls, cog, system, poll):
		async def f(button, interaction):
			await interaction.response.edit_message(
				content = '......',
				view = None
			)
			member = interaction.user
			assert member is not None

			result = await system.remove_votes(poll, interaction.user)
			if result is None:
				# Due
				await interaction.message.edit(content = cog._trans(interaction, 'empty-failed'))
			else:
				await interaction.message.edit(content = cog._trans(interaction, 'empty-success'))
				if len(result) > 0:
					peek: Event = result[0]
					async with poll.mutex:
						if poll.processed_order == peek.processed_order:
							await cog._render(poll)

class VoteCommands(BaseCog, name = 'Vote'):
	'''
	Main missions to complete: poll and bet.
	Recommended type vote (up to 25) or old-style vote (up to characters limit).
	'''
	def __init__(self, bot: Bot):
		super().__init__(bot)
		self.poll_system = PollHoldSystem(db['poll_system'] if config('POLL_DB_BASED', default = False, cast = bool) else None)
		# self.bet_system = BetHoldSystem(db['bet_system'] if config('BET_DB_BASED', default = False, cast = bool) else None)
		self.restore_view: List[VoteOptionView] = []
		for poll in self.poll_system.restore_poll():
			NotImplemented

	async def cog_before_invoke(self, ctx):
		await self._cog_before_invoke(ctx)

	@discord.slash_command(
		description = 'Create a poll',
		guild_only = True,
		options = [
			discord.Option(str,
				name = 'title',
				description = 'The title of this poll'
			),
			discord.Option(int,
				name = 'period',
				description = 'How long is the poll active (Default 1 [period_unit])',
				default = 1,
				min_value = 1),
			discord.Option(str,
				name = 'period_unit',
				description = 'What unit of time is used (Default to "hour")',
				choices = time_units_options,
				default = 'h'),
			discord.Option(bool,
				name = 'realtime',
				description = 'Whether the result is shown in realtime (Default to false)',
				default = False),
			discord.Option(bool,
				name = 'show_name',
				description = 'Whether the voter names are shown in result (Default to false)',
				default = False),
			discord.Option(bool,
				name = 'show_name_voting',
				description = 'Whether the voter names are shown in voting if "real_time" is true (Override show_name)',
				default = None),
			discord.Option(bool,
				name = 'show_name_result',
				description = 'Whether the voter names are shown in result (Override show_name)',
				default = None),
			discord.Option(int,
				name = 'num_votes',
				description = 'How many votes to cast (Default to 1)',
				default = 1,
				min_value = 0),
			discord.Option(int,
				name = 'min_votes',
				description = 'What the minimum number of votes to cast is (Override num_votes)',
				default = None,
				min_value = 0),
			discord.Option(int,
				name = 'max_votes',
				description = 'What the maximum number of votes to cast is (Override num_votes)',
				default = None,
				min_value = 0),
			discord.Option(str,
				name = 'options',
				description = 'Options to vote.'
			)
		]
	)
	async def poll(self, ctx,
		title: str,
		period: int,
		period_unit,
		realtime: bool,
		show_name: bool,
		show_name_voting: Optional[bool],
		show_name_result: Optional[bool],
		num_votes: int,
		min_votes: Optional[int],
		max_votes: Optional[int],
		options: str):
		'''
		`/{cmd_name} <?period> <?period_unit> <?realtime> <?show_name> <?show_name_voting> <?show_name_result>
		<?num_votes> <?min_votes> <?max_votes> <options>` creates a poll with specified options.
		The options are listed and separated by spaces, and every redundant option gets omitted.
		By default, this command generates a one-hour poll with single vote without showing details.
		Can be only called in a server channel.
		'''
		atleast = config('POLL_PERIOD_ATLEAST', default = 60, cast = int)
		if (p := period_to_delta(period, period_unit)) and p.total_seconds() < atleast:
			# Valid in semantics but too tricky to use
			await send_error_embed(ctx,
				name = self._trans(ctx, 'too-short-period-error'),
				value = self._trans(ctx, 'too-short-period-error-value', format = {'period': period, 'default': atleast}),
				ephemeral = True
			)

		options: List[str] = StringArgumentParser.pick(options)
		max_options = config('POLL_MAXIMUM_OPTIONS', default = 20, cast = int)
		if len(options) > max_options:
			await send_error_embed(ctx,
				name = self._trans(ctx, 'too-many-options-error'),
				value = self._trans(ctx, 'too-many-options-error-value', format = {'default': max_options, 'n': len(options)}),
				ephemeral = True
			)

		poll = Poll(ctx.author, ctx.channel, title, options, period, period_unit, realtime, show_name, show_name_voting, show_name_result, num_votes, min_votes, max_votes)
		interaction = await ctx.send_response(content = self._trans(ctx, 'creating_poll_message'))
		message = await interaction.original_message() # NOT interaction.message!
		poll.connect_to_msg(message)
		# If no errors, the poll is valid...
		await self.poll_system.register(poll, self._timeout_process(poll))
		# Build embed
		async with poll.mutex:
			# To remind me that we should get lock before rendering.
			# The mutex here is not necessary, though.

			# If processed_order is right...
			await self._render(poll, message = message)

	async def _render(self, poll: BasePoll, message = None, end = False):
		'''
		This method does not handle anything about processing order and mutex locks.
		'''
		if message is None:
			try:
				message = await poll.channel.fetch_message(poll.msg_id)
			except discord.NotFound:
				# Silent error
				return

		channel = poll.channel
		assert isinstance(channel, (discord.abc.GuildChannel, discord.Thread))
		locale = channel.guild.preferred_locale

		if isinstance(poll, Poll):
			await self._render_field_poll(poll, locale, message, end)
		else:
			raise AttributeError("Unknown poll type to render.")

	async def _render_field_poll(self, poll: Poll, locale, message, end = False):
		show_result = False
		show_name = False
		if end:
			show_result = True
			show_name = poll.show_name_result
		else:
			show_result = poll.realtime
			show_name = poll.show_name_voting

		if show_result:
			votes = poll.get_votes_per_option()
			total_votes = sum(votes.values())

		kwargs = {'content': None}

		# The color is set to be randomly fixed according to the title
		embed = discord.Embed(title = poll.title, color = discord.Color.random(hash(poll.title)))
		for option, n in votes.items():
			name = f'{self._trans(locale, 'render-option-order')}{option}'
			value = discord.Empty
			if show_result:
				p = round(n * 10000 / total_votes)
				result_text = f'{n}/{total_votes}({p // 100}.{p % 100}%)'

				if show_name and n > 0:
					voters = poll.vote_receive[option].elements() # Poll only allows 0 or 1 in Counter
					voters_id = [f'<@{voter.id}>' for voter in voters]
					name_text = ' '.join(voters_id)
					value = f'{result_text}\n{name_text}'
				else:
					value = result_text
			embed.add_field(name = name, value = value)
		kwargs['embed'] = embed

		if not end and len(message.components) == 0:
			kwargs['view'] = VoteOptionView(poll,
				self._trans(locale, 'vote'),
				PollController.vote_action(self, poll_system, poll),
				self._trans(locale, 'lookup'),
				PollController.lookup_action(self, poll_system, poll),
				self._trans(locale, 'early'),
				PollController.early_action(self, poll_system, poll),
				self._trans(locale, 'cancel'),
				PollController.cancel_action(self, poll_system, poll)
			)
		elif end:
			kwargs['view'] = None

		await message.edit(**kwargs)

	async def _timeout_process(self, poll: BasePoll):
		# This method is called in locked mutex (ensured in HoldSystem)
		await self._render(poll, end = True)

	#async def _ending(self, poll: BasePoll):
		# This method needs to be called in locked mutex
		#...

	async def cog_command_error(self, ctx, exception: discord.ApplicationCommandError):
		match exception:
			case NonPositivePeriodError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'invalid-period-error'),
					value = self._trans(ctx, 'invalid-period-error-value', format = {'period': exception.period}),
					ephemeral = True
				)
			case EmptyChoiceError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'empry-choice-error'),
					value = self._trans(ctx, 'empry-choice-error-value'),
					ephemeral = True
				)
			case MinMaxError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'min-max-error'),
					value = self._trans(ctx, 'min-max-error-value', format = {'min': exception.min, 'max': exception.max}),
					ephemeral = True
				)
			case ZeroVoteError():
				await send_error_embed(ctx,
					name = self._trans(ctx, 'zero-vote-error'),
					value = self._trans(ctx, 'zero-vote-error-value'),
					ephemeral = True
				)
			case _:
				# Propagate
				await super().cog_command_error(ctx, exception)

class NonPositivePeriodError(discord.ApplicationCommandError):
	def __init__(self, period):
		self.period = period

class EmptyChoiceError(discord.ApplicationCommandError):
	pass

class MinMaxError(discord.ApplicationCommandError):
	def __init__(self, min, max):
		self.min = min
		self.max = max

class ZeroVoteError(discord.ApplicationCommandError):
	pass

def setup(bot):
	cog = VoteCommands(bot)
	bot.add_cog(cog)
	for view in cog.restore_view:
		bot.add_view(view)