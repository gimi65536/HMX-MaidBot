from .types import *
from .ops import BinaryOperator, TernaryOperator, UnaryOperator
from sympy import E, Expr, I, S
from sympy.parsing.sympy_parser import (
	parse_expr,
	auto_symbol,
	repeated_decimals,
	auto_number,
	factorial_notation,
	convert_xor,
	implicit_multiplication,
	convert_equals_signs,
	rationalize
)

class LengthOperator(UnaryOperator):
	def eval(self, mapping):
		a = self.extract_constant(*self.eval_operands(mapping))[0]

		if not a.is_str:
			raise ValueError('Only apply to strings')

		return NumberConstant(len(a.value))

'''
The function invokes a more flexible parser provided by SymPy with:
auto_symbol, repeated_decimals (0.2[1] to 0.2111...), auto_number,
factorial_notation (5! = 120), convert_xor (3^2 is 3**2),
implicit_multiplication (sin(1)cos(1) is sin(1)*cos(1)),
convert_equals_signs (1 = 1 is 1 == 1), and rationalize
to parse a complicated numeric expressions into number constants.
This implies that the operator is independent from the parser
of the calculator, and users need to write expressions in terms of
what SymPy wants.

Specially, we make "i/j/J" be I, "e" be E, and 'Pi/PI' be pi.

Note that an equality check with variables "x = 5" cannot be written
in "x == 5" because "'x' is a variable, not a constant 5" (identical)
unless we put all the information of the mapping into the parser
to let the parser know "'x' is 5" to generate results directly.
If we put all the contexts (mapping), we can solve the problem,
but the mapping is thought to be large and the expression to be small.
Therefore, we choose to parse the expression TWICE: to find all free
variables, and injure the needed variables by local_dict.

Also, of course, the function using SymPy parser cannot handle any
assignment clauses to interfere the variable spaces.
'''
class SymParseOperator(UnaryOperator):
	transformations = (
		auto_symbol,
		repeated_decimals,
		auto_number,
		factorial_notation,
		convert_xor,
		implicit_multiplication,
		convert_equals_signs,
		rationalize
	)
	def eval(self, mapping):
		a = self.extract_constant(*self.eval_operands(mapping))[0]

		if not a.is_str:
			raise ValueError('Only apply to strings')

		s = a.value

		# Boolean parse
		if s == 'TRUE' or s == 'True' or s == 'true':
			return BooleanConstant(True)
		elif s == 'FALSE' or s == 'False' or s == 'false':
			return BooleanConstant(False)

		try:
			local_dict = {
				'i': I,
				'j': I,
				'J': I,
				'e': E,
				'Pi': S.Pi,
				'PI': S.Pi,
			}
			expr = parse_expr(s, transformations = self.transformations, local_dict = local_dict)
			free_symbols = expr.free_symbols
			for symbol in free_symbols:
				v = Var(symbol)
				if v not in mapping:
					raise ValueError(f'The expression includes undefined variable {symbol}')
				c = mapping.get(v).content
				if c.is_str:
					raise ValueError(f'The variable {symbol} is a string')
				if c.is_bool:
					if c.value:
						local_dict[symbol] = S.true
					else:
						local_dict[symbol] = S.false
				else:
					local_dict[symbol] = c.value

			n = parse_expr(s, transformations = self.transformations, local_dict = local_dict)

			if isinstance(n, Expr):
				return NumberConstant(n)
			elif n is S.true:
				return BooleanConstant(True)
			elif n is S.false:
				return BooleanConstant(False)
		except:
			pass

		return a

class StrictSymParseOperator(ParseOperator):
	def eval(self, mapping):
		result = super().eval(mapping)

		if result.is_str:
			raise ValueError(f'Cannot parse {result.value} into a number/Boolean value')

		return result
