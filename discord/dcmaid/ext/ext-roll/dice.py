from . import DiscordDigitRollGame
from ...utils import int_to_emoji
from rollgames.dice import *

class DiscordDiceGame(DiscordDigitRollGame, DiceGame):
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordDigitRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		DiceGame.__init__(self, self.processed_kwargs['faces'], random)

class DiscordDiceNGame(DiscordDigitRollGame):
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordDigitRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		for base in type(self).__bases__:
			if issubclass(base, DiceNGame):
				base.__init__(self, random)
				return

class DiscordDice4Game(DiscordDiceNGame, Dice4Game):
	pass

class DiscordDice6Game(DiscordDiceNGame, Dice6Game):
	pass

class DiscordDice8Game(DiscordDiceNGame, Dice8Game):
	pass

class DiscordDice10Game(DiscordDiceNGame, Dice10Game):
	pass

class DiscordDice12Game(DiscordDiceNGame, Dice12Game):
	pass

class DiscordDice20Game(DiscordDiceNGame, Dice20Game):
	pass
