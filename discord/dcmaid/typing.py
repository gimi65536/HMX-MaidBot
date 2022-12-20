from discord import ApplicationContext, Interaction, PartialMessageable, Thread
from discord.abc import GuildChannel, PrivateChannel
from typing import Any, Optional, Protocol, TypeAlias

class _Localeable1(Protocol):
	locale: Optional[str]

class _Localeable2(Protocol):
	@property
	def locale(self) -> Optional[str]:
		...

class Channelable(Protocol):
	@property
	def channel(self):
		...

QuasiContext: TypeAlias = ApplicationContext | Interaction

# I know it is weird to force QuasiContext localeable instead of just let protocols do everything
# but there are really a few problems... I cannot stop warnings instead of adding this.
Localeable: TypeAlias = _Localeable1 | _Localeable2 | QuasiContext

ChannelType: TypeAlias = GuildChannel | PrivateChannel | PartialMessageable | Thread

__all__ = ('Channelable', 'Localeable', 'QuasiContext')