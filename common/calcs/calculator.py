from .ops_basic import *
from .types import Operator
from collections import Counter
from enum import Enum
from itertools import chain
from typing import Optional
import re

class Associability(Enum):
	NOTCARE = 0
	LEFT = 1
	RIGHT = 2

class OperatorInfo:
	@classmethod
	def factory(cls, op: type[Operator], *symbols: str) -> list['OperatorInfo']:
		return [cls(op, symbol) for symbol in symbols]

	def __init__(self, op: type[Operator], symbol: str):
		# symbol should NOT contain spaces
		self._op = op
		self._symbol = symbol

	@property
	def op(self) -> type[Operator]:
		return self._op

	@property
	def ary(self) -> int:
		return self._op.ary

	@property
	def symbol(self) -> str:
		return self._symbol

class PrecedenceLayer:
	def __init__(self, asso: Associability, *ops: OperatorInfo):
		if asso is Associability.NOTCARE:
			raise ValueError('Associability cannot be NOTCARE')

		self._asso = asso

		c = Counter(o.symbol for o in ops)
		if any(c.items(), (lambda _, i: i > 1)):
			raise ValueError('Two operators with the same symbol in the same precedence!')
		if any(ops, (lambda o: o.ary != 2)):
			raise ValueError(f'All operators should be {ary}-ary')

		self._ops = ops
		self._op_table: dict[str, type[Operator]] = {o.symbol: o.op for o in ops}

	def __iter__(self):
		return iter(self._ops)

	@property
	def asso(self) -> Associability:
		return self._asso

	@property
	def symbols(self) -> list[str]:
		return [o.symbol for o in self._ops]

default_precedence_table = {
	10: PrecedenceLayer(Associability.LEFT,
		OperatorInfo(MultipleOperator, '*'),
		OperatorInfo(DivideOperator, '/'),
		OperatorInfo(IntegerDivideOperator, '//'),
		OperatorInfo(ModuloOperator, '%'),
	),
	20: PrecedenceLayer(Associability.LEFT,
		OperatorInfo(PlusOperator, '+'),
		OperatorInfo(MinusOperator, '-'),
		OperatorInfo(ConcatOperator, '.'),
	),
	70: PrecedenceLayer(Associability.LEFT,
		OperatorInfo(LessOperator, '<'),
		OperatorInfo(LeOperator, '<='),
		OperatorInfo(GreaterOperator, '>'),
		OperatorInfo(GeOperator, '>='),
	),
	80: PrecedenceLayer(Associability.LEFT,
		OperatorInfo(EqualOperator, '=='),
		OperatorInfo(NonequalOperator, '!='),
	),
	110: PrecedenceLayer(Associability.RIGHT,
		OperatorInfo(AndOperator, '&&'),
		OperatorInfo(OrOperator, '||'),
		OperatorInfo(ImplOperator, '->'),
		OperatorInfo(XorOperator, '^'),
		OperatorInfo(IffOperator, '<->'),
	),
}

default_prefix_ops = [
	OperatorInfo(PositiveOperator, '+'),
	OperatorInfo(NegativeOperator, '-'),
	OperatorInfo(NotOperator, '~'),
]

class Lexer:
	spaces = re.compile(r'\s+', re.ASCII)
	word_symbol_split = re.compile(r'(?:\w|[^\x00-\x7f])+|\W+?', re.ASCII)
	check_word = re.compile(r'(?:\w|[^\x00-\x7f])+', re.ASCII)
	ascii_symbols = re.compile(r'\W+', re.ASCII)
	ascii_words = re.compile(r'\w+', re.ASCII)

	def __init__(self, symbols: list[str]):
		ss = []
		for symbol in symbols:
			if len(symbol) == 0:
				raise ValueError('Empty operators are disallowed')
			if symbol.isascii():
				if self.ascii_symbols.fullmatch(symbol):
					ss.append(symbol)
				elif not self.ascii_words.fullmatch(symbol):
					raise ValueError('Operators mixed with symbols and words are disallowed')
			else:
				for c in symbol:
					if c.isascii() or self.ascii_words.match(c):
						continue

					raise ValueError('Operators mixed with symbols and words are disallowed')
				ss.append(symbol)

		self._parse_symbols = set(ss)
		self._find_cache: dict[str, Optional[list[str]]] = {'': []}

	def _find(self, symbols: str) -> Optional[list[str]]:
		if symbols in self._find_cache:
			return self._find_cache[symbols]

		for i in range(len(symbols), 0, -1):
			prefix = symbols[:i]
			if prefix not in self._parse_symbols:
				continue

			sub_result = self._find(symbols[i:])
			if sub_result is None:
				continue

			self._find_cache[symbols] = [prefix, *sub_result]
			return self._find_cache[symbols]

		self._find_cache[symbols] = None
		return None

	def tokenize(self, s: str) -> list[str]:
		# First step split
		first = self.spaces.split(s)
		# Second step divide alphanumeric and ASCII symbols
		second = []
		for token in first:
			second.extend(self.word_symbol_split.findall(token))
		result = []
		for token in second:
			if self.check_word.fullmatch(token):
				result.append(token)
				continue

			find = self._find(token)
			if find is None:
				raise ValueError(f'Parse error with the symbols "{token}"')
			result.extend(find)

		return result

class Calculator:
	_ptable: dict[int, PrecedenceLayer]
	_special = '(,)'
	_special_re = re.compile(r'[\(,\)]')

	def __init__(self, prefix_ops: list[OperatorInfo], ptable: list[PrecedenceLayer] | dict[int, PrecedenceLayer]):
		if isinstance(ptable, list):
			self._ptable = {i: p for i, p in enumerate(ptable)}
		else:
			self._ptable = ptable.copy()

		self._prefix_ops = prefix_ops.copy()

		infix_symbols = list(chain.from_iterable(layer.symbols for layer in self._ptable.values()))
		c = Counter(infix_symbols)
		if any(c.items(), (lambda _, i: i > 1)):
			raise ValueError('Two infix operators with the same symbol!')

		# Prefix operator can be overloaded... like functions

		symbols = infix_symbols + [prefix_op.symbol for prefix_op in self._prefix_ops]
		# Sanitize
		for symbol in symbols:
			if self._special_re.search(symbol):
				raise ValueError(f'Operator cannot includes the following symbols: "{self._special}"')

		symbols.extend(self._special)
		self._lexer = Lexer(symbols)

		self._infix_table: dict[str, Operator] = {op_info.symbol: op_info.op for op_info in chain.from_iterable(self._ptable.values())}
		self._infix_precedence_table: dict[str, int] = {op_info.symbol: precedence for precedence, layer in self._ptable.items() for op_info in layer}
		self._infix_asso_table: dict[str, Associability] = {op_info.symbol: layer.asso for precedence, layer in self._ptable.items() for op_info in layer}

		self._prefix_table: dict[str, Operator] = {op_info.symbol: op_info.op for op_info in self._prefix_ops}
		...