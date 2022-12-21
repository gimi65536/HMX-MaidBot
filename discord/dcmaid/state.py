import discord
from collections.abc import Mapping
from threading import Lock
from typing import cast, Optional

class State:
	def __init__(self) -> None:
		# To ensure that each update is handled by mutex lock,
		# the "object" part is recommended to be immutable.
		self._real_dict: dict[str, tuple[Lock, object]] = {}
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
	def __contains__(self, key: str):
		return key in self._real_dict
	def remove(self, key: str):
		if key in self._real_dict:
			lock = self._real_dict[key][0]
			with lock:
				del self._real_dict[key]
	def get_installed_hooks(self, channel_id: int) -> Optional[Mapping[str, discord.Webhook]]:
		return cast(Optional[Mapping[str, discord.Webhook]], self.get(f'installed_hooks_{channel_id}'))
	def set_installed_hooks(self, channel_id: int, immutable_map: Mapping[str, discord.Webhook]):
		self.set(f'installed_hooks_{channel_id}', immutable_map)
	def remove_installed_hooks(self, channel_id):
		self.remove(f'installed_hooks_{channel_id}')