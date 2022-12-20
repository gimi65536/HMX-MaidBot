from discord import ApplicationContext, Interaction, PartialMessageable, Thread
from discord.abc import GuildChannel, PrivateChannel
from typing import Any, Protocol, TypeAlias

class Localeable(Protocol):
	locale: str

class Channelable(Protocol):
	@property
	def channel(self):
		...

QuasiContext: TypeAlias = ApplicationContext | Interaction

ChannelType: TypeAlias = GuildChannel | PrivateChannel | PartialMessageable | Thread

__all__ = ('Channelable', 'Localeable', 'QuasiContext')