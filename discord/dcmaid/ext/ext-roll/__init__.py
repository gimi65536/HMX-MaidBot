import discord
from rollgames import BaseRollGame, BaseRollGameMeta
from simple_parsers.string_argument_parser import StringArgumentParser
from types import MappingProxyType
from typing import Any, Dict, List, Tuple, Type
from ..roll import ArgumentLengthError
from ...utils import send_as

_registered_games: Dict[str, Type['DiscordRollGame']] = {}
registered_games = MappingProxyType(_registered_games)

_all_mapping_table: Dict[str, Type['DiscordRollGame']] = {}
all_mapping_table = MappingProxyType(_all_mapping_table)

class DiscordRollGameMeta(BaseRollGameMeta):
	def __new__(mcls, *args, reg = False, **kwargs):
		cls = super().__new__(mcls, *args, **kwargs)
		if reg:
			_registered_games[cls.game_name] = cls

			_all_mapping_table[cls.game_name] = cls
			for name in cls.game_data.names.values():
				_all_mapping_table[name] = cls
			for alia in cls.game_data.alias:
				_all_mapping_table[alia] = cls

		return cls

class DiscordRollGame(BaseRollGame, metaclass = DiscordRollGameMeta):
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

class DiscordDigitRollGame(DiscordRollGame):
	async def _process(self, i: int):
		return int_to_emoji(i)
