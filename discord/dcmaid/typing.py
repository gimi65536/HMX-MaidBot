from typing import Protocol

class Localeable(Protocol):
	locale: str

__all__ = ('Localeable', )