from . import DiscordRollGame
from ...utils import int_to_emoji
from rollgames import DiceGame

class DiscordDiceGame(DiscordRollGame, DiceGame):
	options = {
		1: [('faces', int)]
	}

	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordRollGame.__init__(ctx, webhook, arguments, initial_text, kwargs)
		DiceGame.__init__(self.faces, random)

	async def _process(self, i: int):
		return int_to_emoji(i)