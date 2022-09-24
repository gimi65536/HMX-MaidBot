from . import DiscordRollGame
from ...utils import int_to_emoji
from rollgames import DiceGame

class DiscordDiceGame(DiscordRollGame, DiceGame):
	options = {
		1: [('faces', int)]
	}

	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordRollGame.__init__(ctx, webhook, arguments, initial_text, kwargs)
		DiceGame.__init__(self.processed_kwargs['faces'], random)

	async def _process(self, i: int):
		return int_to_emoji(i)

class DiscordDiceNGame(DiscordRollGame, DiceGame):
	options = {
		0: []
	}
	N: int

	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordRollGame.__init__(ctx, webhook, arguments, initial_text, kwargs)
		DiceGame.__init__(self.N, random)

	async def _process(self, i: int):
		return int_to_emoji(i)

class DiscordDice4Game(DiscordDiceNGame):
	N = 4

class DiscordDice6Game(DiscordDiceNGame):
	N = 6

class DiscordDice8Game(DiscordDiceNGame):
	N = 8

class DiscordDice10Game(DiscordDiceNGame):
	N = 10

class DiscordDice12Game(DiscordDiceNGame):
	N = 12

class DiscordDice20Game(DiscordDiceNGame):
	N = 20