from .types import *
from .ops import BinaryOperator

class AssignOperator(BinaryOperator):
	def eval(self, mapping):
		a, b = self.eval_operands(mapping)
		b = self.extract_constant(b)

		if not a.is_lvalue:
			raise ValueError('Only applies for variables')

		a.content = b.without_dummy()
		return a
