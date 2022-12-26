from discord import (
	ApplicationContext,
	CategoryChannel,
	DMChannel,
	ForumChannel,
	GroupChannel,
	Interaction,
	Message,
	PartialMessageable,
	SlashCommand,
	SlashCommandGroup,
	StageChannel,
	TextChannel,
	Thread,
	VoiceChannel,
)
from discord.abc import GuildChannel as GuildChannelAbc, PrivateChannel as PrivateChannelAbc
from typing import Optional, Protocol, runtime_checkable, TypeAlias, TYPE_CHECKING

if TYPE_CHECKING:
	# MessageableChannel is also a useful type in runtime...
	from discord.abc import MessageableChannel
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

# I know it is weird to force QuasiContext localeable instead of just let protocols do everything
# but there are really a few problems... I cannot stop warnings instead of adding this.
Localeable: TypeAlias = _Localeable1 | _Localeable2

# Following are types that can be used in runtime codes for, exactly, isinstance() method.

QuasiContext: TypeAlias = ApplicationContext | Interaction

GuildChannel: TypeAlias = TextChannel | VoiceChannel | CategoryChannel | ForumChannel | StageChannel

PrivateChannel: TypeAlias = DMChannel | GroupChannel | PartialMessageable

ChannelType: TypeAlias = GuildChannel | PrivateChannel | PartialMessageable | Thread

GuildChannelType: TypeAlias = GuildChannel | Thread

MessageableGuildChannel: TypeAlias = TextChannel | VoiceChannel | Thread

# Since the type of .channel is too complex, we use positive list instead of Protocols
Channelable: TypeAlias = QuasiContext | Message

SlashType: TypeAlias = SlashCommand | SlashCommandGroup

Threadable: TypeAlias = TextChannel | ForumChannel

# These types of channels can have webhooks, but the Webhook.channel is only of TextChannel.
Webhookable: TypeAlias = TextChannel | VoiceChannel | ForumChannel

__all__ = (
	'Channelable',
	'ChannelType',
	'GuildChannel',
	'GuildChannelAbc',
	'PrivateChannel',
	'PrivateChannelAbc',
	'MessageableChannel',
	'MessageableGuildChannel',
	'GuildChannelType',
	'Localeable',
	'QuasiContext',
	'SlashType',
	'Threadable',
	'Webhookable'
)