from discord import ApplicationContext, Interaction
from typing import Any, Protocol, TypeAlias

class Localeable(Protocol):
	locale: str

class Channelable(Protocol):
	channel: Any

QuasiContext: TypeAlias = ApplicationContext | Interaction

__all__ = ('Channelable', 'Localeable', 'QuasiContext')