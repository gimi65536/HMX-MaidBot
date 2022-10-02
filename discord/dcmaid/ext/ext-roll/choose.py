from . import DiscordRollGame
from rollgames.choose import *

class DiscordChooseGame(DiscordRollGame, ChooseGame, reg = True):
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		ChooseGame.__init__(self, *self.processed_kwargs, random)

class _DiscordSampleNGame(DiscordRollGame):
	# To activate this __init__, please make this class the first parent class
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		DiscordRollGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		type(self).__bases__[1].__init__(self, *self.processed_kwargs, random)

class DiscordChooseMultiGame(_DiscordSampleNGame, ChooseMultiGame, reg = True):
	pass

class DiscordRepeatChooseGame(_DiscordSampleNGame, RepeatChooseGame, reg = True):
	pass

__all__ = (
	"DiscordChooseGame",
	"DiscordChooseMultiGame",
	"DiscordRepeatChooseGame"
)