import discord.abc
from discord import (
	ApplicationContext,
	DMChannel,
	GroupChannel,
	Interaction,
	PartialMessageable,
	TextChannel,
	Thread,
	VoiceChannel,
)
from discord.abc import GuildChannel, PrivateChannel
from typing import Any, Optional, Protocol, TypeAlias

class _Localeable1(Protocol):
	locale: Optional[str]

class _Localeable2(Protocol):
	@property
	def locale(self) -> Optional[str]:
		...

class _Channelable1(Protocol):
	channel: Any

class _Channelable2(Protocol):
	@property
	def channel(self):
		...

Channelable: TypeAlias = _Channelable1 | _Channelable2

QuasiContext: TypeAlias = ApplicationContext | Interaction

# I know it is weird to force QuasiContext localeable instead of just let protocols do everything
# but there are really a few problems... I cannot stop warnings instead of adding this.
Localeable: TypeAlias = _Localeable1 | _Localeable2# | QuasiContext

ChannelType: TypeAlias = GuildChannel | PrivateChannel | PartialMessageable | Thread

GuildChannelType: TypeAlias = GuildChannel | Thread

MessageableGuildChannel: TypeAlias = TextChannel | VoiceChannel | Thread

__all__ = (
	'Channelable',
	'ChannelType',
	'MessageableGuildChannel',
	'GuildChannelType',
	'Localeable',
	'QuasiContext',
)
