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
from typing import Any, Optional, Protocol, runtime_checkable, TypeAlias, TYPE_CHECKING

if TYPE_CHECKING:
	# MessageableChannel is also a useful type in runtime...
	MessageableChannel: TypeAlias = discord.abc.MessageableChannel
else:
	MessageableChannel: TypeAlias = TextChannel | VoiceChannel | Thread | DMChannel | PartialMessageable | GroupChannel

@runtime_checkable
class _Localeable1(Protocol):
	locale: Optional[str]

@runtime_checkable
class _Localeable2(Protocol):
	@property
	def locale(self) -> Optional[str]:
		...

@runtime_checkable
class _Channelable1(Protocol):
	channel: MessageableChannel

@runtime_checkable
class _Channelable2(Protocol):
	@property
	def channel(self):
		...

Channelable: TypeAlias = _Channelable1 | _Channelable2

# I know it is weird to force QuasiContext localeable instead of just let protocols do everything
# but there are really a few problems... I cannot stop warnings instead of adding this.
Localeable: TypeAlias = _Localeable1 | _Localeable2

# Following are types that can be used in runtime codes for, exactly, isinstance() method.

QuasiContext: TypeAlias = ApplicationContext | Interaction

ChannelType: TypeAlias = GuildChannel | PrivateChannel | PartialMessageable | Thread

GuildChannelType: TypeAlias = GuildChannel | Thread

MessageableGuildChannel: TypeAlias = TextChannel | VoiceChannel | Thread

__all__ = (
	'Channelable',
	'ChannelType',
	'MessageableChannel',
	'MessageableGuildChannel',
	'GuildChannelType',
	'Localeable',
	'QuasiContext',
)