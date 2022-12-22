from __future__ import annotations
import discord
from case_insensitive_dict import CaseInsensitiveDict
from collections.abc import Mapping, MutableMapping
from rollgames import BaseRollGame, BaseRollGameMeta
from types import MappingProxyType
from typing import TYPE_CHECKING
from ...typing import QuasiContext
from ...utils import get_author, send_as, int_to_emoji

_registered_games: MutableMapping[str, type[DiscordRollGame]] = CaseInsensitiveDict()

_all_mapping_table: MutableMapping[str, type[DiscordRollGame]] = CaseInsensitiveDict()

if TYPE_CHECKING:
	from proxy_types import _MappingProxyType
	from typing import cast
	registered_games: Mapping[str, type[DiscordRollGame]] = _MappingProxyType(_registered_games)
	all_mapping_table: Mapping[str, type[DiscordRollGame]] = _MappingProxyType(_all_mapping_table)
else:
	registered_games = MappingProxyType(_registered_games)
	all_mapping_table = MappingProxyType(_all_mapping_table)

class DiscordRollGameMeta(BaseRollGameMeta):
	def __new__(mcls, *args, reg = False, **kwargs):
		if TYPE_CHECKING:
			cls = cast(type['DiscordRollGame'], super().__new__(mcls, *args, **kwargs))
		else:
			cls = super().__new__(mcls, *args, **kwargs)

		if reg:
			assert cls.game_name is not None
			_registered_games[cls.game_name] = cls

			_all_mapping_table[cls.game_name] = cls
			for name in cls.game_data.names.values():
				_all_mapping_table[name] = cls
			for alia in cls.game_data.alias:
				_all_mapping_table[alia] = cls

		return cls

class DiscordRollGame(BaseRollGame, metaclass = DiscordRollGameMeta):
	def __init__(self, ctx: discord.Message | QuasiContext, webhook, arguments: str, initial_text = None, send_options = {}):
		self.ctx = ctx
		self.webhook = webhook
		self.initial = initial_text
		self.send_options = send_options
		self.processed_kwargs, self.variant = self._preprocess_args(arguments)
		self.for_text_cmd = False
		self.player = get_author(ctx)

		if isinstance(ctx, discord.Message):
			self.initial = None
			self.for_text_cmd = True
			self.locale = None
		else:
			self.locale = ctx.locale

	async def _send(self, content):
		if self.initial is not None:
			# The verbose is enabled if initial is given
			length = ... if self.variant else len(self.processed_kwargs)
			verbose = type(self).game_data.get_verbose(length, self.locale)
			if verbose is not None:
				verbose = verbose.format(*self._verbose_argiter())
				content = f'{self.initial} {verbose}\n{content}'
			else:
				content = f'{self.initial}\n{content}'
		elif self.for_text_cmd:
			if self.player is not None:
				content = f'<@{self.player.id}>\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.send_options)

class DiscordDigitRollGame(DiscordRollGame):
	async def _process(self, i: int):
		return int_to_emoji(i)
