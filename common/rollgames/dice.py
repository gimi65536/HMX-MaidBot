from . import BaseRollGame

class DiceGame(BaseRollGame, name = 'dice'):
	options = {
		1: [('faces', int)]
	}

	def __init__(self, faces: int, random):
		self.faces = faces
		self.random = random

	def _verbose_argiter(self):
		return (self.faces, )

	def _roll(self) -> int:
		return self.random.randint(1, self.faces)

class DiceNGame(DiceGame):
	'''
	This class cannot be initialize (lack N to fill in)
	'''
	options = {
		0: []
	}
	N: int

	def __init__(self, random):
		super().__init__(self.N, random)

	def _verbose_argiter(self):
		return []

class Dice4Game(DiceNGame, name = 'dice4'):
	N = 4

class Dice6Game(DiceNGame, name = 'dice6'):
	N = 6

class Dice8Game(DiceNGame, name = 'dice8'):
	N = 8

class Dice10Game(DiceNGame, name = 'dice10'):
	N = 10

class Dice12Game(DiceNGame, name = 'dice12'):
	N = 12

class Dice20Game(DiceNGame, name = 'dice20'):
	N = 20
