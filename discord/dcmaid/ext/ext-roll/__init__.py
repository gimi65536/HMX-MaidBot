import discord
from rollgames import BaseRollGame, BaseRollGameMeta
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Tuple, Type
from ..roll import ArgumentLengthError
from ...typing import QuasiContext
from ...utils import send_as, int_to_emoji

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
	def __init__(self, ctx: QuasiContext, webhook, arguments: str, initial_text = None, send_options = {}):
		self.ctx = ctx
		self.webhook = webhook
		self.initial = initial_text
		self.options = send_options
		self.processed_kwargs = self._preprocess_args(arguments)

	def _verbose_argiter(self) -> Iterable:
		return self.processed_kwargs.values()

	async def _send(self, content):
		if self.initial is not None:
			# The verbose is enabled if initial is given
			verbose = self.game_data.get_verbose(len(self.processed_kwargs), self.ctx.locale)
			if verbose is not None:
				# The python dict preserves insertion order, and we maintain the argument order the abstract game wants.
				verbose = verbose.format(*self._verbose_argiter())
				content = f'{self.initial} {verbose}\n{content}'
			else:
				content = f'{self.initial}\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.options)

class DiscordDigitRollGame(DiscordRollGame):
	async def _process(self, i: int):
		return int_to_emoji(i)
