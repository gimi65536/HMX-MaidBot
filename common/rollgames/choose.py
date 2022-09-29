from . import BaseRollGame
from typing import Iterable

class ChooseGame(BaseRollGame, name = 'choose'):
	options = {
		...: [('first', str), ('choices', str)]
	}

	def __init__(self, first: str, choices: Iterable[str], random):
		l = [first]
		l.extend(choices)
		self.choices = l
		self.random = random

	def _roll(self) -> str:
		return self.random.choice(self.choices)

	def _verbose_argiter(self):
		return (' '.join(f'`{n}`' for n in self.choices), )