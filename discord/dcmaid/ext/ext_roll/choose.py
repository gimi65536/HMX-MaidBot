from . import DiscordRollGame
from rollgames.choose import *

class _DiscordSampleGame(DiscordRollGame):
	async def _process(self, s: str):
		return f'**{s}**'

class DiscordChooseGame(_DiscordSampleGame, ChooseGame, reg = True):
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		_DiscordSampleGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		ChooseGame.__init__(self, *self.processed_kwargs.values(), random) # type: ignore

class _DiscordSampleNGame(_DiscordSampleGame):
	# To activate this __init__, please make this class the first parent class
	def __init__(self, ctx, webhook, arguments, random, initial_text = None, **kwargs):
		_DiscordSampleGame.__init__(self, ctx, webhook, arguments, initial_text, kwargs)
		type(self).__bases__[1].__init__(self, *self.processed_kwargs.values(), random) # type: ignore

	async def _process(self, l):
		return f"""**{' '.join(f'`{c}`' for c in l)}**"""

class DiscordChooseMultiGame(_DiscordSampleNGame, ChooseMultiGame, reg = True):
	pass

class DiscordRepeatChooseGame(_DiscordSampleNGame, RepeatChooseGame, reg = True):
	pass

__all__ = (
	"DiscordChooseGame",
	"DiscordChooseMultiGame",
	"DiscordRepeatChooseGame"
)
