from . import BaseRollGame

class DiceGame(BaseRollGame, name = 'dice'):
	options = {
		1: [('faces', int)]
	}

	def __init__(self, faces: int, random):
		self.faces = faces
		self.random = random

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

class Dice4Game(DiceGame, name = 'dice4'):
	N = 4

class Dice6Game(DiceGame, name = 'dice6'):
	N = 6

class Dice8Game(DiceGame, name = 'dice8'):
	N = 8

class Dice10Game(DiceGame, name = 'dice10'):
	N = 10

class Dice12Game(DiceGame, name = 'dice12'):
	N = 12

class Dice20Game(DiceGame, name = 'dice20'):
	N = 20