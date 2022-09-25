from . import BaseRollGame

class DiceGame(BaseRollGame):
	options = {
		1: [('faces', int)]
	}
	game_name = 'dice'

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
	game_name = 'dice{N}'

	def __init__(self, random):
		super().__init__(self.N, random)
		self.game_name = self.game_name.format(N = self.N)

class Dice4Game(DiceGame):
	N = 4

class Dice6Game(DiceGame):
	N = 6

class Dice8Game(DiceGame):
	N = 8

class Dice10Game(DiceGame):
	N = 10

class Dice12Game(DiceGame):
	N = 12

class Dice20Game(DiceGame):
	N = 20