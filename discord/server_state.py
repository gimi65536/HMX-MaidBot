import discord
from threading import Lock
from load_db import db
from typing import Dict, Optional, Tuple

class _State:
	def __init__(self):
		# To ensure that each update is handled by mutex lock,
		# the "object" part is recommended to be immutable.
		self._real_dict: Dict[str, Tuple[Lock, object]] = {}
	def get(self, key: str, default: object = None):
		try:
			t = self._real_dict[key]
		except KeyError:
			return default
		else:
			return t[1]
	def set(self, key: str, obj: object):
		if key not in self._real_dict:
			self._real_dict[key] = (Lock(), obj)
		else:
			lock = self._real_dict[key][0]
			with lock:
				self._real_dict[key] = (lock, obj)
	def get_installed_hooks(self, channel_id: int) -> Optional[Tuple[discord.Webhook, ...]]:
		return self.get(f'installed_hooks_{channel_id}')
	def set_installed_hooks(self, channel_id: int, immutable_list: Tuple[discord.Webhook, ...]):
		self.set(f'installed_hooks_{channel_id}', immutable_list)

# Importing is already threading-safe in python, so we don't need to concern this:
state = _State()

__all__ = ['state']