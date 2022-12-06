from .types import *
from .ops import BinaryOperator, TernaryOperator, UnaryOperator
from sympy import ceiling, Float, floor, Integer, Number
from sympy.core.random import rng, random_complex_number

class RandomOperator(UnaryOperator):
	def eval(self, mapping):
		a = self.extract_constant(*self.eval_operands(mapping))[0]

		if not a.is_dummy:
			rng.seed(str(a.value))

		return NumberConstant(Float(rng.random()))

class RandomIntOperator(TernaryOperator):
	ary = 3
	def eval(self, mapping):
		s, a, b = self.extract_constant(*self.eval_operands(mapping))

		if (a.is_number and b.is_number) and (a.value.is_real and b.value.is_real):
			if a.value > b.value:
				a, b = b, a
			na = ceiling(a.value)
			nb = floor(b.value)
			if na > nb:
				raise ValueError('Not valid interval: no integer is included')

			if not s.is_dummy:
				rng.seed(str(s.value))

			return NumberConstant(Integer(rng.randint(int(na), int(nb))))

		raise ValueError('Only apply real numbers as input')

class RandomRealOperator(TernaryOperator):
	def eval(self, mapping):
		s, a, b = self.extract_constant(*self.eval_operands(mapping))

		if (a.is_number and b.is_number) and (a.value.is_real and b.value.is_real):
			if not s.is_dummy:
				rng.seed(str(s.value))

			return NumberConstant(Number(rng.uniform(a.value, b.value)))

		raise ValueError('Only apply real numbers as input')

class RandomComplexOperator(Operator):
	ary = 5
	def eval(self, mapping):
		s, a, b, c, d = self.extract_constant(*self.eval_operands(mapping))

		if (a.is_number and b.is_number) and (a.value.is_real and b.value.is_real and c.value.is_real and d.value.is_real):
			if not s.is_dummy:
				rng.seed(str(s.value))

			return NumberConstant(random_complex_number(a.value, c.value, b.value, d.value))

		raise ValueError('Only apply real numbers as input')
