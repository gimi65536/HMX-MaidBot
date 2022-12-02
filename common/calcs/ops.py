from .types import Constant, NumType, Operator, ResultType, Value
from typing import Callable, Optional

class UnaryOperator(Operator):
	ary = 1

class BinaryOperator(Operator):
	ary = 2
	'''
	table: Optional[dict[type[Constant], dict[type[Constant], ResultType]]] = None

	def _exec_coercion(self, callable: Callable[[NumType, NumType], NumType]) -> Value:
		a, b = coercion(self.extract_constant())
		t = type(a)
		return t(callable(a, b))
	'''

class TernaryOperator(Operator):
	ary = 3