from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Iterator, Mapping
from importlib.resources import files
from more_itertools import repeat_last, SequenceView
from reader import load
from simple_parsers.string_argument_parser import StringArgumentParser
from types import EllipsisType, MappingProxyType
from typing import Any, ClassVar, Optional

class GameData:
	def __init__(self, d: dict[Any, Any]):
		self._d = d

	@staticmethod
	def _get(table: dict[Any, Any], locale: Optional[str]) -> Any:
		return table.get(locale, table.get(None, None))

	def get_name(self, locale: Optional[str] = None) -> str:
		return str(self._get(self._d.get('name', {}), locale))

	@property
	def names(self) -> Mapping[Any, Any]:
		return MappingProxyType(self._d.get('name', {}))

	def get_description(self, locale: Optional[str] = None) -> str:
		return str(self._get(self._d.get('description', {}), locale))

	@property
	def descriptions(self) -> Mapping[Any, Any]:
		return MappingProxyType(self._d.get('description', {}))

	def get_help_dict(self) -> dict[Any, Any]:
		return {(i if i != 'variant' else ...): MappingProxyType(d) for i, d in self._d.get('help', {}).items()}

	def get_help(self, n, locale: Optional[str] = None) -> Optional[str]:
		if n is ...:
			n = 'variant'
		table = self._d.get('help', {}).get(n, {})
		return self._get(table, locale)

	def get_verbose(self, n, locale: Optional[str] = None) -> Optional[str]:
		if n is ...:
			n = 'variant'
		table = self._d.get('verbose', {}).get(n, {})
		return self._get(table, locale)

	@property
	def alias(self):
		return SequenceView(self._d.get('alias', []))

class BaseRollGameMeta(ABCMeta):
	base_game_data: ClassVar[Optional[dict[Any, Any]]] = None
	processed_options: ClassVar[set[Any]] = set()
	game_name: Optional[str]
	'''
	game_name is a class property that assigned by "name" arguments when creating classes.
	This game_name is a code name, not for human-read.
	You should avoid using spaces in game_name, instead use spaces in the human-readable names and alias.
	'''
	game_data: GameData
	'''
	game_data stores some information.
	'''
	options: Optional[dict[EllipsisType | int, list[tuple[str, type]]]]
	'''
	The class property "options" is to declare argument information and activate the preprocessor.
	However, you still need to call __init__ of abstract games after you get the processed arguments.
	For example, you define:
	```
	... in AbstractGame
	options = {
		0: [],
		1: [('example', str)],
		2: [('foo', int), ('bar', str)]
	}
	def __init__(self, foo, bar): ...
	```
	in your abstract games, and you need to use:
	```
	... in ActualGame
	self.processed_kwargs = self._preprocess_args(arguments)
	AbstractGame.__init__(self.processed_kwargs['foo'], self.processed_kwargs['bar'])
	```
	in your actual games for Discord, etc.

	This design is to make the abstract games "keep pure" by not touching `self.processed_kwargs`
	and let the actual games have more power to decide how to pass arguments to their parents.
	However, it is recommended to make actual games correspond to specific abstract games, i.e.,
	one-to-one to share the metadata (e.g. help) in different platforms.
	'''
	def __new__(mcls, *args, name: Optional[str] = None):
		if mcls.base_game_data is None:
			d = load(files(__package__) / 'games')
			if d is None:
				mcls.base_game_data = {}
			else:
				if not isinstance(d, dict):
					raise ValueError('The topmost element of the games.* file should be in dict-like type')
				mcls.base_game_data = d

		cls = super().__new__(mcls, *args)

		if name is not None:
			cls.game_name = name

		mcls.__fall_base(cls, 'game_name')
		cls.game_data = GameData(mcls.base_game_data.get(cls.game_name, {}))

		mcls.__fall_base(cls, 'options')
		if cls.options is None:
			# The basic classes have not declared options yet.
			return cls

		options = cls.options
		if id(options) not in mcls.processed_options:
			mcls.processed_options.add(id(options))
			ellipsis_l = None
			for n, l in list(options.items()): # Early expand to delete keys
				if n is ...:
					# Processed later
					ellipsis_l = l
					continue

				assert isinstance(n, int)
				if len(l) < n:
					# Drop key
					options.pop(n)
				elif len(l) > n:
					# Reduce list
					options[n] = l[:n]

			if ellipsis_l is not None:
				length = len(ellipsis_l)
				if length == 0:
					# Invalid
					options.pop(...)
				elif any(n >= length - 1 for n in options.keys() if n is not ...): # type: ignore
					# Drop ... due to ambiguity
					options.pop(...)

		return cls

	@staticmethod
	def __fall_base(cls, property):
		if getattr(cls, property, None) is None:
			for base in cls.__bases__:
				setattr(cls, property, getattr(base, property, None))
				if getattr(cls, property) is not None:
					return

class BaseRollGame(metaclass = BaseRollGameMeta):
	# The necessary arguments are passed in __init__

	@abstractmethod
	def _roll(self):
		# _roll() is implemented in games
		pass

	async def _process(self, obj):
		# _process() is specified in each actual class
		return str(obj)

	def _verbose_argiter(self) -> Iterable:
		return []

	@abstractmethod
	async def _send(self, content):
		# _send() is implemented in each platform
		# content is not necessary to be a string,
		# everything is your choice.
		pass

	@classmethod
	def _preprocess_args(cls, arguments) -> tuple[dict[str, Any], bool]:
		if cls.options is None:
			raise AttributeError('Invalid preprocess on basic game classes!')

		if arguments is None:
			arguments = ''

		args = StringArgumentParser.pick(arguments)
		len_args = len(args)
		ellipsis = False
		start_ellipsis = -1
		if len_args not in cls.options:
			if ... in cls.options and len_args >= len(cls.options[...]) - 1:
				ellipsis = True
				start_ellipsis = len(cls.options[...])
			else:
				raise ArgumentLengthError(expect = list((f'{len(options) - 1}+' if i is ... else str(i)) for i, options in cls.options.items()), got = len_args)

		processed: dict[str, Any] = {}

		args_option: Iterator[tuple[str, type]]
		if ellipsis:
			args_option = repeat_last(cls.options[...])
			ellipsis_attr = cls.options[...][-1][0]
		else:
			args_option = iter(cls.options[len_args])
			ellipsis_attr = '' # For consistence

		for i, ((attr, t), arg) in enumerate(zip(args_option, args), 1):
			try:
				value = t(arg)
				if ellipsis:
					if i == start_ellipsis:
						processed[attr] = []
					if i >= start_ellipsis:
						processed[attr].append(value)
					else:
						processed[attr] = value
				else:
					processed[attr] = value
			except:
				raise ArgumentTypeError(i, t, arg)

		if ellipsis and ellipsis_attr not in processed:
			processed[ellipsis_attr] = []

		return processed, ellipsis

	async def run(self):
		result = self._roll()
		content = await self._process(result)
		await self._send(content)

class ArgumentLengthError(ValueError):
	def __init__(self, expect: list[str], got: int):
		self.expect = expect
		self.got = got

class ArgumentTypeError(TypeError):
	def __init__(self, order: int, t: type, got: str):
		self.order = order
		self.t = t
		self.got = got

class GameNotFound(AttributeError):
	def __init__(self, name: str):
		self.name = name
