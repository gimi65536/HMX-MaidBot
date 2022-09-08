from dataclasses import dataclass

@dataclass
class Maid:
	name: str
	display_name: str
	avatar_base64: str

__all__ = ['Maid']