from dataclasses import dataclass

@dataclass
class Maid:
	name: str
	display_name: str
	avatar: bytes

__all__ = ['Maid']
