import discord
from rollgames import BaseRollGame
from simple_parsers.string_argument_parser import StringArgumentParser
from typing import Any, Dict, List, Tuple
from .roll import ArgumentLengthError
from ...utils import send_as

class DiscordRollGame(BaseRollGame):
	options: Dict[int, List[Tuple[str, type]]] = {
		0: [],
		1: [('example', str)]
	}

	def __init__(self, ctx, webhook, arguments: str, initial_text = None, send_options = {}):
		self.ctx = ctx
		self.webhook = webhook
		self.initial = initial_text
		self.options = send_options
		self.processed_kwargs = self._preprocess_args(arguments)

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

	async def _send(self, content):
		if self.initial is not None:
			content = f'{self.initial}\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.options)
