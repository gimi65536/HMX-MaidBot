from .types import *
from .ops import BinaryOperator, NullaryOperator, TernaryOperator, UnaryOperator
from sympy import ceiling, Float, floor, Integer, Number
from sympy.core.random import rng, random_complex_number

class RandomOperator(NullaryOperator):
	def eval(self, mapping):
		return NumberConstant(Float(rng.random()))

class RandomWithSeedOperator(UnaryOperator):
	def eval(self, mapping):
		a = self.extract_constant(*self.eval_operands(mapping))[0]

		if not a.is_dummy:
			rng.seed(str(a.value))

		return NumberConstant(Float(rng.random()))

class _RandomIntOperator:
	def _eval(self, a: Constant, b: Constant, seed = None):
		if (a.is_number and b.is_number) and (a.value.is_real and b.value.is_real):
			if a.value > b.value:
				a, b = b, a
			na = ceiling(a.value)
			nb = floor(b.value)
			if na > nb:
				raise ValueError('Not valid interval: no integer is included')

			if seed is not None and not seed.is_dummy:
				rng.seed(str(seed.value))

			return NumberConstant(Integer(rng.randint(int(na), int(nb))))

		raise ValueError('Only apply real numbers as input')

class RandomIntOperator(BinaryOperator, _RandomIntOperator):
	def eval(self, mapping):
		a, b = self.extract_constant(*self.eval_operands(mapping))

		return self._eval(a, b)

class RandomIntWithSeedOperator(TernaryOperator, _RandomIntOperator):
	def eval(self, mapping):
		s, a, b = self.extract_constant(*self.eval_operands(mapping))

		return self._eval(a, b, s)

class _RandomRealOperator:
	def _eval(self, a: Constant, b: Constant, seed = None):
		if (a.is_number and b.is_number) and (a.value.is_real and b.value.is_real):
			if seed is not None and not seed.is_dummy:
				rng.seed(str(seed.value))

			return NumberConstant(Number(rng.uniform(a.value, b.value)))

		raise ValueError('Only apply real numbers as input')

class RandomRealOperator(BinaryOperator, _RandomRealOperator):
	def eval(self, mapping):
		a, b = self.extract_constant(*self.eval_operands(mapping))

		return self._eval(a, b)

class RandomRealWithSeedOperator(TernaryOperator, _RandomRealOperator):
	def eval(self, mapping):
		s, a, b = self.extract_constant(*self.eval_operands(mapping))

		return self._eval(a, b, s)

class _RandomComplexOperator:
	def _eval(self, a: Constant, b: Constant, c: Constant, d: Constant, seed = None):
		if (a.is_number and b.is_number) and (a.value.is_real and b.value.is_real and c.value.is_real and d.value.is_real):
			if seed is not None and not seed.is_dummy:
				rng.seed(str(seed.value))

			return NumberConstant(random_complex_number(a.value, c.value, b.value, d.value))

		raise ValueError('Only apply real numbers as input')

class RandomComplexWithSeedOperator(Operator, _RandomComplexOperator):
	ary = 4
	def eval(self, mapping):
		a, b, c, d = self.extract_constant(*self.eval_operands(mapping))

		return self._eval(a, b, c, d)

class RandomComplexWithSeedOperator(Operator, _RandomComplexOperator):
	ary = 5
	def eval(self, mapping):
		s, a, b, c, d = self.extract_constant(*self.eval_operands(mapping))

		return self._eval(a, b, c, d, s)
