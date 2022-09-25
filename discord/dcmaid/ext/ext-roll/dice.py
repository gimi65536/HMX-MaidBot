from . import DiscordDigitRollGame
from ...utils import int_to_emoji
from rollgames.dice import *

class DiscordDiceGame(DiscordDigitRollGame, DiceGame):
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordDigitRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		DiceGame.__init__(self, self.processed_kwargs['faces'], random)

class _DiscordDiceNGame(DiscordDigitRollGame):
	# To activate this __init__, please make this class the first parent class
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordDigitRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		type(self).__bases__[1].__init__(self, random)

class DiscordDice4Game(_DiscordDiceNGame, Dice4Game):
	pass

class DiscordDice6Game(_DiscordDiceNGame, Dice6Game):
	pass

class DiscordDice8Game(_DiscordDiceNGame, Dice8Game):
	pass

class DiscordDice10Game(_DiscordDiceNGame, Dice10Game):
	pass

class DiscordDice12Game(_DiscordDiceNGame, Dice12Game):
	pass

class DiscordDice20Game(_DiscordDiceNGame, Dice20Game):
	pass
