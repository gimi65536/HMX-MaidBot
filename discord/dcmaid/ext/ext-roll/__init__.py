import discord
from rollgames import BaseRollGame
from simple_parsers.string_argument_parser import StringArgumentParser
from typing import Any, Dict, List, Tuple
from .roll import ArgumentLengthError
from ...utils import send_as

class DiscordRollGame(BaseRollGame):
	def __init__(self, ctx, webhook, arguments: str, initial_text = None, send_options = {}):
		self.ctx = ctx
		self.webhook = webhook
		self.initial = initial_text
		self.options = send_options
		self.processed_kwargs = self._preprocess_args(arguments)

	async def _send(self, content):
		if self.initial is not None:
			content = f'{self.initial}\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.options)
