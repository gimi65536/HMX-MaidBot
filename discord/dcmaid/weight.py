import discord
import random
from threading import Lock
from typing import Optional
from .basebot import Bot
from .utils import proxy

class Weight:
	creation_lock = Lock()
	col_name = 'channel-maids-weight'
	field_name = 'weights'
	bot_key = '____bot'
	d: dict[tuple[Bot, discord.abc.GuildChannel], 'Weight'] = {}

	@staticmethod
	def _get_key(bot, channel):
		return (bot, channel)

	@staticmethod
	def _get_filter(channel):
		return {'channel': channel.id, 'channel_type': channel.type.value}

	def __init__(self, bot: Bot, channel: discord.abc.GuildChannel):
		assigned = False
		self.bot = bot
		self.channel = channel
		key = self._get_key(bot, channel)
		d = self.d
		if key not in d:
			with self.creation_lock:
				# Ensure that each instabce of the same channel shares the same table.
				if key in d:
					# Some instance has already created when locking
					pass
				else:
					# Create a real instance
					assigned = True
					d[key] = self

					self._individual_lock = Lock()
					col = self._col = bot.db[self.col_name]
					maids = self._maids = bot.maids
					data = col.find_one({'channel_id': channel.id})
					if data is None:
						weights = {}
					else:
						weights = data.get(self.field_name, {})

					modified = False
					# Fetch maids
					for recorded_maid in weights:
						if recorded_maid != self.bot_key and recorded_maid not in maids:
							# Who?
							modified = True
							weights.pop(recorded_maid)

					if self.bot_key not in weights:
						# Bot field
						modified = True
						weights[self.bot_key] = 1 # Default

					for maid in maids:
						if maid not in weights:
							modified = True
							weights[maid] = 1 # Default

					if modified:
						filter = self._get_filter(channel)
						col.replace_one(
							filter = filter,
							replacement = {**filter, 'weights': weights},
							upsert = True
						)

					self._weights = weights
					self._random = random.Random()

		if not assigned:
			self._proxy: 'Weight' = d[(bot, channel)]

	@proxy
	def get_maid_weight(self, maid_name: str) -> int:
		return self._weights[maid_name]

	@proxy
	def get_bot_weight(self) -> int:
		return self._weights[self.bot_key]

	def _update(self, key: str, i: int):
		# Called in the internal singleton, so no proxy
		with self._individual_lock:
			self._weights[key] = i
			self._upload()

	def _upload(self):
		filter = self._get_filter(self.channel)
		self._col.replace_one(
			filter = filter,
			replacement = {**filter, 'weights': self._weights},
			upsert = True
		)

	@proxy
	def set_maid_weight(self, maid_name: str, i: int):
		ori_i = self._weights[maid_name]
		if ori == i:
			return
		if i < 0:
			i = 0
		self._update(maid_name, i)

	@proxy
	def set_bot_weight(self, i: int):
		ori_i = self._weights[self.bot_key]
		if ori == i:
			return
		if i < 0:
			i = 0
		self._update(self.bot_key, i)

	def _reset_weights(self):
		with self._individual_lock:
			self._weights = {self.bot_key: 1}
			self._weights.update({maid: 1 for maid in self._maids})
			self._upload()

	@proxy
	def random_get(self, random_generator = None) -> Optional[str]:
		# None for bot
		if random_generator is None:
			random_generator = self._random

		items = list(self._weights.items())
		try:
			result = random_generator.choices([i[0] for i in items], [i[1] for i in items])[0]
		except ValueError:
			self._reset_weights()
			return self.random_get(random_generator)

		if result == self.bot_key:
			return None
		return result
