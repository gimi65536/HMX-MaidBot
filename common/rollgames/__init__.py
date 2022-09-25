from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

class BaseRollGame(ABC):
	options: Dict[int, List[Tuple[str, type]]]
	'''
	The class property "options" is here in an abstract game to activate the preprocessor.
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

	game_name: str
	'''
	game_name is assumed to be a variable of an instance.
	Please do not assume it to be a class property.
	'''

	# The necessary arguments are passed in __init__

	@abstractmethod
	def _roll(self):
		# _roll() is implemented in games
		pass

	@abstractmethod
	async def _process(self, obj):
		# _process() is specified in each actual class
		pass

	@abstractmethod
	async def _send(self, content):
		# _send() is implemented in each platform
		# content is not necessary to be a string,
		# everything is your choice.
		pass

	@classmethod
	def _preprocess_args(cls, arguments) -> Dict[str, Any]:
		if arguments is None:
			arguments = ''

		args = StringArgumentParser.pick(arguments)
		len_args = len(args)
		if len_args not in cls.options:
			raise ArgumentLengthError(expect = list(cls.options.keys()), got = len_args)
		args_option = options[len_args]
		processed = {}

		for i, ((attr, t), arg) in enumerate(zip(args_option, args), 1):
			try:
				processed[attr] = t(arg)
			except:
				raise ArgumentTypeError(i, t, arg)

		return processed

	async def run(self):
		result = self._roll()
		content = await self._process(result)
		await self._send(content)

class ArgumentLengthError(ValueError):
	def __init__(self, expect: List[int], got: int):
		self.expect = expect
		self.got = got

class ArgumentTypeError(TypeError):
	def __init__(self, order: int, t: type, got: str):
		self.order = order
		self.t = t
		self.got = got
