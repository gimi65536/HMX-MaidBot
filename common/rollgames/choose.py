from . import BaseRollGame
from typing import Iterable, List

class AbstractSampleGame(BaseRollGame):
	choices: List[str]

	def __init__(self, first: str, choices: Iterable[str], random):
		l = [first]
		l.extend(choices)
		self.choices = l
		self.random = random

	async def _process(self, s: str):
		return f'**{s}**'

class ChooseGame(AbstractSampleGame, name = 'choose'):
	options = {
		...: [('first', str), ('choices', str)]
	}

	def __init__(self, first: str, choices: Iterable[str], random):
		super().__init__(first, choices, random)

	def _roll(self) -> str:
		return self.random.choice(self.choices)

class AbstractSampleNGame(AbstractSampleGame):
	def __init__(self, n: int, first: str, choices: Iterable[str], random):
		super().__init__(first, choices, random)
		self.n = n

	def _verbose_argiter(self):
		return (str(self.n), ' '.join(f'`{c}`' for c in self.choices))

class ChooseMultiGame(AbstractSampleNGame, name = 'choose-multi'):
	options = {
		...: [('n', int), ('first', str), ('choices', str)]
	}

	def __init__(self, n: int, first: str, choices: Iterable[str], random):
		super().__init__(n, first, choices, random)
		if len(self.choices) < self.n:
			self.n = len(self.choices)

	def _roll(self) -> str:
		return self.random.sample(self.choices, self.n)

class RepeatChooseGame(AbstractSampleNGame, name = 'repeat-choose'):
	options = ChooseMultiGame.options

	def __init__(self, n: int, first: str, choices: Iterable[str], random):
		super().__init__(n, first, choices, random)

	def _roll(self) -> str:
		return self.random.choices(self.choices, k = self.n)
