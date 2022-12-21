from dataclasses import dataclass
from typing import Optional

@dataclass
class Maid:
	name: str
	display_name: str
	avatar: Optional[bytes]

__all__ = ['Maid']
