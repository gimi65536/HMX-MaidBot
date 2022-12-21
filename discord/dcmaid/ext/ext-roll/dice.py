from . import DiscordDigitRollGame
from rollgames.dice import *

class DiscordDiceGame(DiscordDigitRollGame, DiceGame, reg = True):
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordDigitRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		DiceGame.__init__(self, self.processed_kwargs['faces'], random)

class _DiscordDiceNGame(DiscordDigitRollGame):
	# To activate this __init__, please make this class the first parent class
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordDigitRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		type(self).__bases__[1].__init__(self, random) # type: ignore

class DiscordDice4Game(_DiscordDiceNGame, Dice4Game, reg = True):
	pass

class DiscordDice6Game(_DiscordDiceNGame, Dice6Game, reg = True):
	pass

class DiscordDice8Game(_DiscordDiceNGame, Dice8Game, reg = True):
	pass

class DiscordDice10Game(_DiscordDiceNGame, Dice10Game, reg = True):
	pass

class DiscordDice12Game(_DiscordDiceNGame, Dice12Game, reg = True):
	pass

class DiscordDice20Game(_DiscordDiceNGame, Dice20Game, reg = True):
	pass

__all__ = (
	"DiscordDiceGame",
	"DiscordDice4Game",
	"DiscordDice6Game",
	"DiscordDice8Game",
	"DiscordDice10Game",
	"DiscordDice12Game",
	"DiscordDice20Game"
)