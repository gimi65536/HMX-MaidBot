from discord import ApplicationContext, Interaction
from typing import Protocol, TypeAlias, Union

class Localeable(Protocol):
	locale: str

QuasiContext: TypeAlias = Union[ApplicationContext, Interaction]

__all__ = ('Localeable', 'QuasiContext')