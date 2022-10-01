from discord import ApplicationContext, Interaction
from typing import Any, Protocol, TypeAlias, Union

class Localeable(Protocol):
	locale: str

class Channelable(Protocol):
	channel: Any

QuasiContext: TypeAlias = Union[ApplicationContext, Interaction]

__all__ = ('Channelable', 'Localeable', 'QuasiContext')