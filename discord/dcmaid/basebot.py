from __future__ import annotations
import discord
import re
from .maid import Maid
from .utils import generate_config
from base64 import b64decode
from collections.abc import Mapping
from pymongo import ASCENDING
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from pymongo.database import Database
	from typing import Optional
	from .state import State

config = generate_config(
	MAID_LIST_COLLECTION = {'default': 'maid-list'},
)

class Bot(discord.Bot):
	def __init__(self, db: Database, state: State, description: Optional[str] = None, *args, **options):
		super().__init__(description, *args, **options)
		self._db = db
		self._state = state
		self._maids = self._retrieve_maids(db)

	@staticmethod
	def _data_base64_to_bytes(img):
		if (m := re.fullmatch(r'data:image/.*;base64,(.+)', img)):
			return b64decode(m.group(1))

	@classmethod
	def _retrieve_maids(cls, db: Database) -> Mapping[str, Maid]:
		# The maids information is loaded once per execution.
		_maids = list(db[config['MAID_LIST_COLLECTION']].find().sort("_id", ASCENDING))
		_maids_list = list(Maid(m['name'], m['display_name'], cls._data_base64_to_bytes(m['avatar'])) for m in _maids)
		# This dict provides a way to retrieve maids by names.
		# Also, with the features of dict, the maid order is kept.
		maids: Mapping[str, Maid] = MappingProxyType({m.name: m for m in _maids_list})
		return maids

	@property
	def db(self):
		return self._db

	@property
	def state(self):
		return self._state

	@property
	def maids(self):
		return self._maids
