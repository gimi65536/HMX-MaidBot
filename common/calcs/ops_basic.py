from .types import *
from .ops import BinaryOperator

class PlusOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant(*self.eval_operands())

		if a.is_str or b.is_str:
			a, b = a.to_str(), b.to_str()
			return StringConstant(a.value + b.value)
		elif a.is_bool and b.is_bool:
			return BooleanConstant(a.value or b.value)
		else:
			a, b = a.to_number(), b.to_number()
			return NumberConstant(a.value + b.value)

class MinusOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant(*self.eval_operands())

		if a.is_str or b.is_str:
			raise ValueError('Invalid string subtraction')
		elif a.is_bool and b.is_bool:
			return BooleanConstant(a.value and not b.value)
		else:
			a, b = a.to_number(), b.to_number()
			return NumberConstant(a.value - b.value)

class MultipleOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant(*self.eval_operands())

		if a.is_str or b.is_str:
			# a:num/bool b:str
			if a.is_str:
				a, b = b, a

			if a.is_str:
				# Both a, b are str
				raise ValueError('Invalid string multiplication')

			if a.is_bool:
				a = a.to_number()

			if not (a.value.is_integer and a.value.nonnegative):
				raise ValueError('String multiplication is valid only for non-negative integer')

			return StringConstant(a.value * b.value)
		elif a.is_bool and b.is_bool:
			return BooleanConstant(a.value and b.value)
		else:
			a, b = a.to_number(), b.to_number()
			return NumberConstant(a.value * b.value)

class DivideOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant(*self.eval_operands())

		if a.is_number and b.is_number:
			return NumberConstant(a.value / b.value)
		else:
			raise ValueError('Invalid type division')

class IntegerDivideOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant(*self.eval_operands())

		if a.is_number and b.is_number:
			return NumberConstant(a.value // b.value)
		else:
			raise ValueError('Invalid type division')

class ModuloOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant(*self.eval_operands())

		if a.is_number and b.is_number:
			return NumberConstant(a.value % b.value)
		else:
			raise ValueError('Invalid type division')
