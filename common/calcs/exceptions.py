class UserDefinedError(Exception):
	pass

class LexerConstructError(ValueError):
	pass

class TokenizeError(ValueError):
	def __init__(self, position: int, s: str):
		super().__init__(p, s)

	def __str__(self):
		return f'At column {self.args[0]}: {self.args[1]}'
