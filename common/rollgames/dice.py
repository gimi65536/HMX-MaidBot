from . import BaseRollGame

class DiceGame(BaseRollGame):
	def __init__(self, faces: int, random):
		self.faces = faces
		self.random = random

	def _roll(self) -> int:
		return self.random.randint(1, self.faces)