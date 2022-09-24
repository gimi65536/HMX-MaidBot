import discord
from rollgames import BaseRollGame
from typing import Dict, List, Tuple
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
		self._preprocess_args(arguments)

	def _preprocess_args(self, arguments):
		args = arguments.split()
		len_args = len(args)
		if len_args not in self.options:
			raise ArgumentLengthError(expect = list(self.options.keys()), got = len_args)
		args_option = options[len_args]

		for i, ((attr, t), arg) in enumerate(zip(args_option, args), 1):
			try:
				setattr(self, attr) = t(arg)
			except:
				raise ArgumentTypeError(i, t, arg)

	async def _send(self, content):
		if self.initial is not None:
			content = f'{self.initial}\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.options)
