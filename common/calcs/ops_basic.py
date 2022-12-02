from .coercion import coercion
from .numtypes import *
from .ops import BinaryOperator

class PlusOperator(BinaryOperator):
	def exec(self):
		a, b = coercion(self.extract_constant())
		t = type(a)
		if t is BooleanConstant:
			return BooleanConstant(a.value | b.value)

		return t(a.value + b.value)

class MinusOperator(BinaryOperator):
	def exec(self):
		a, b = coercion(self.extract_constant())
		t = type(a)
		if t is BooleanConstant:
			return a.value and not b.value
		elif t is StringConstant:
			raise ValueError('Invalid string subtraction')

		return t(a.value + b.value)

class MultipleOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant()
		ta, tb = type(a), type(b)
		if ta is StringConstant or tb is StringConstant:
			if ta is IntegerConstant or tb is IntegerConstant:
				return StringConstant(a.value * b.value)
			else:
				raise ValueError('Invalid string multiplication')

		if ta is BooleanConstant or tb is BooleanConstant:
			raise ValueError('Invalid Boolean multiplication')

		a, b = coercion(a, b)
		t = type(a)
		return t(a.value * b.value)

class DivideOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant()
		ta, tb = type(a), type(b)
		if ta is BooleanConstant or tb is BooleanConstant or ta is StringConstant or tb is StringConstant:
			raise ValueError('Invalid type division')

		if ta is IntegerConstant and tb is IntegerConstant:
			a = a.cast(FractionConstant)

		a, b = coercion(a, b)
		t = type(a)
		return t(a.value / b.value)

class IntegerDivideOperator(BinaryOperator):
	def exec(self):
		a, b = self.extract_constant()
		ta, tb = type(a), type(b)
		if ta is BooleanConstant or tb is BooleanConstant or ta is StringConstant or tb is StringConstant:
			raise ValueError('Invalid type division')

		...

class ModOperator(BinaryOperator):
	...
