from abc import ABC, abstractmethod

class BaseRollGame(ABC):
	# The necessary arguments are passed in __init__

	@abstractmethod
	def _roll(self):
		# _roll() is implemented in games
		pass

	@abstractmethod
	async def _process(self, obj):
		# _process() is specified in each actual class
		pass

	@abstractmethod
	async def _send(self, content):
		# _send() is implemented in each platform
		# content is not necessary to be a string,
		# everything is your choice.
		pass

	async def run(self):
		result = self._roll()
		content = await self._process(result)
		await self._send(content)