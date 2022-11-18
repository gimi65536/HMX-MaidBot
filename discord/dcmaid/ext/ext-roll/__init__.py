import discord
from case_insensitive_dict import CaseInsensitiveDict
from collections.abc import Mapping, MutableMapping
from rollgames import BaseRollGame, BaseRollGameMeta
from types import MappingProxyType
from typing import Any, cast, Union
from ..roll import ArgumentLengthError
from ...typing import QuasiContext
from ...utils import send_as, int_to_emoji

_registered_games: MutableMapping[str, type['DiscordRollGame']] = CaseInsensitiveDict()
registered_games: Mapping[str, type['DiscordRollGame']] = MappingProxyType(_registered_games)

_all_mapping_table: MutableMapping[str, type['DiscordRollGame']] = CaseInsensitiveDict()
all_mapping_table: Mapping[str, type['DiscordRollGame']] = MappingProxyType(_all_mapping_table)

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
	def __init__(self, ctx: Union[discord.Message, QuasiContext], webhook, arguments: str, initial_text = None, send_options = {}):
		self.ctx = ctx
		self.webhook = webhook
		self.initial = initial_text
		self.options = send_options
		self.processed_kwargs, self.variant = self._preprocess_args(arguments)
		self.for_text_cmd = False

		if isinstance(self.ctx, discord.Message):
			self.initial = None
			self.for_text_cmd = True

	async def _send(self, content):
		if self.initial is not None:
			# The verbose is enabled if initial is given
			length = ... if self.variant else len(self.processed_kwargs)
			verbose = self.game_data.get_verbose(length, self.ctx.locale)
			if verbose is not None:
				verbose = verbose.format(*self._verbose_argiter())
				content = f'{self.initial} {verbose}\n{content}'
			else:
				content = f'{self.initial}\n{content}'
		elif self.for_text_cmd:
			self.for_text_cmd = cast(self.ctx, discord.Message)
			content = f'<@{self.ctx.author.id}>\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.options)

class DiscordDigitRollGame(DiscordRollGame):
	async def _process(self, i: int):
		return int_to_emoji(i)
