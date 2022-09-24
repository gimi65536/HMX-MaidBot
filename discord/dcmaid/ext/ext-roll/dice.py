from . import DiscordRollGame
from ...utils import int_to_emoji
from rollgames import DiceGame

class DiscordDiceGame(DiscordRollGame, DiceGame):
	def __init__(self, ctx, webhook, faces: int, random, initial_text = None, **kwargs):
		DiscordRollGame.__init__(ctx, webhook, initial_text, kwargs)
		DiceGame.__init__(faces, random)

	async def _process(self, i: int):
		return int_to_emoji(i)