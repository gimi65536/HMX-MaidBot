from .types import *
from .ops import BinaryOperator, TernaryOperator, UnaryOperator

class ToStringOperator(UnaryOperator):
	# Just do str() to the contents of the constants
	def eval(self, mapping):
		a = self.eval_and_extract_constant(0, mapping)

		return StringConstant(str(a.value))

class PrintOperator(UnaryOperator):
	# For numbers, the function returns expressions of primary types: int float complex
	def eval(self, mapping):
		a = self.eval_and_extract_constant(0, mapping)

		if a.is_number:
			n = a.value
			if n.is_integer:
				return StringConstant(str(n))
			if n.is_real:
				return StringConstant(str(n.evalf()))
			c = complex(n)
			real = str(int(c.real)) if c.real.is_integer() else str(c.real)
			imag = str(int(c.imag)) if c.imag.is_integer() else str(c.imag)
			return StringConstant(f'({real}+{imag}j)')
		else:
			return StringConstant(str(a.value))

class PassOperator(BinaryOperator):
	def eval(self, mapping):
		return self.eval_operands(mapping)[1]

class ReverseOperator(UnaryOperator):
	def eval(self, mapping):
		operand = self._operands[0]
		if isinstance(operand, Operator):
			node = type(operand)(*reversed(operand._operands))
			return node.eval(mapping)

		raise ValueError('Can only applied to an operation node')

class DummizeOperator(UnaryOperator):
	def eval(self, mapping):
		a = self.eval_and_extract_constant(0, mapping)

		return a.with_dummy()

class DedummizeOperator(UnaryOperator):
	def eval(self, mapping):
		a = self.eval_and_extract_constant(0, mapping)

		return a.without_dummy()
