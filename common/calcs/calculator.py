from .ops_basic import *
from .types import Operator, TreeNodeType
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
	SQ = "'"
	DQ = '"'
	BACKSLASH = '\\'
	space = re.compile(r'\s', re.ASCII)
	ascii_word = re.compile(r'\w', re.ASCII)
	check_word = re.compile(r'(?:\w|[^\x00-\x7f])+', re.ASCII)
	ascii_symbols = re.compile(r'\W+', re.ASCII)
	ascii_words = re.compile(r'\w+', re.ASCII)

	class S(Enum):
		SYMBOL = 0
		WORD = 1
		INQUOTE = 2
		INQUOTE_ESCAPE = 3

	@classmethod
	def _constant_injure(cls, ld):
		ld['SQ'] = cls.SQ
		ld['DQ'] = cls.DQ
		ld['BACKSLASH'] = cls.BACKSLASH

		ld['S'] = cls.S

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

	@classmethod
	def is_word(cls, c):
		return not c.isascii() or cls.ascii_word.match(c)

	@classmethod
	def is_string(cls, s):
		return s.startswith(cls.SQ) or s.startswith(cls.DQ)

	def tokenize(self, s: str) -> list[str]:
		self._constant_injure(locals())
		# First step split
		first = []
		status = S.SYMBOL
		keep, quote = '', DQ
		for c in s:
			match status:
				case S.INQUOTE_ESCAPE:
					# Only escape that \? = ?
					keep += c
					status = S.INQUOTE
				case S.INQUOTE:
					if quote == c:
						first.append(keep + c)
						keep = ''
						status = S.SYMBOL
					elif quote == BACKSLASH:
						status = S.INQUOTE_ESCAPE
					else:
						keep += c
				case S.SYMBOL:
					if self.is_word(c):
						if len(keep) > 0:
							first.append(keep)
						keep = c
						status = S.WORD
					elif c == SQ or c == DQ:
						if len(keep) > 0:
							first.append(keep)
						keep = c
						quote = c
						status = INQUOTE
					elif c == BACKSLASH:
						raise ValueError('Parse error with the backslash outside quotes')
					elif self.space.match(c):
						if len(keep) > 0:
							first.append(keep)
						keep = ''
					else:
						keep += c
				case S.WORD:
					if self.is_word(c):
						keep += c
					elif c == SQ or c == DQ:
						if len(keep) > 0:
							first.append(keep)
						keep = c
						quote = c
						status = INQUOTE
					elif c == BACKSLASH:
						raise ValueError('Parse error with the backslash outside quotes')
					elif self.space.match(c):
						if len(keep) > 0:
							first.append(keep)
						keep = ''
					else:
						if len(keep) > 0:
							first.append(keep)
						keep = c
						status = S.SYMBOL

		if status == INQUOTE or status == INQUOTE_ESCAPE:
			raise ValueError('Quote not closed')
		if len(keep) > 0:
			first.append(keep)

		result = []
		for token in first:
			if token.startswith(SQ) or token.startswith(DQ):
				result.append(token)
				continue

			if self.check_word.fullmatch(token):
				result.append(token)
				continue

			find = self._find(token)
			if find is None:
				raise ValueError(f'Parse error with the symbols "{token}"')
			result.extend(find)

		return result

class Parser:
	LP = '('
	RP = ')'
	COMMA = ',' # Acts like a binary infix operator with the lowest prec and left-asso
	SQ = Lexer.SQ
	DQ = Lexer.DQ
	QUOTE = SQ + DQ
	BACKSLASH = Lexer.BACKSLASH
	SPECIAL = LP + RP + COMMA + QUOTE + BACKSLASH
	_special = SPECIAL
	_special_re = re.compile(f'[{re.escape(_special)}]')

	class S(Enum):
		INITIAL = 0
		WAIT_LITERAL = 1
		WAIT_INFIX = 2

	class SyntaxTreeNode:
		def __init__(self, content: str):
			self.content = content

		_is_word: bool
		_is_str: bool
		_is_op: bool
		_is_prefix_op: bool
		_is_parentheses: bool
		_is_tuple: bool

		@property
		def is_word(self):
			return self._is_word

		@property
		def is_str(self):
			return self._is_str

		@property
		def is_op(self):
			return self._is_op

		@property
		def is_prefix_op(self):
			return self._is_prefix_op

		@property
		def is_parentheses(self):
			return self._is_parentheses

		@property
		def is_tuple(self):
			return self._is_tuple

	class WordNode(SyntaxTreeNode):
		_is_word = True
		_is_str = False
		_is_op = False
		_is_prefix_op = False
		_is_parentheses = False
		_is_tuple = False

	class StringNode(SyntaxTreeNode):
		_is_word = True
		_is_str = True
		_is_op = False
		_is_prefix_op = False
		_is_parentheses = False
		_is_tuple = False

	class OpNode(SyntaxTreeNode):
		_is_word = False
		_is_str = False
		_is_op = True
		_is_parentheses = False
		_is_tuple = False

	class InfixOPNode(OpNode):
		_is_prefix_op = False

	class PrefixOPNode(OpNode):
		_is_prefix_op = True

	# Not in total_stack
	class ParenthesesNode(SyntaxTreeNode):
		_is_word = False
		_is_str = False
		_is_op = False
		_is_prefix_op = False
		_is_parentheses = True
		_is_tuple = False

	class TupleNode(SyntaxTreeNode):
		_is_word = False
		_is_str = False
		_is_op = False
		_is_prefix_op = False
		_is_parentheses = False
		_is_tuple = True

		def __init__(self, t: tuple[SyntaxTreeNode, ...]):
			self.content = t

	@classmethod
	def _constant_injure(cls, ld):
		ld['LP'] = cls.LP
		ld['RP'] = cls.RP
		ld['COMMA'] = cls.COMMA
		ld['SQ'] = cls.SQ
		ld['DQ'] = cls.DQ
		ld['QUOTE'] = cls.QUOTE
		ld['BACKSLASH'] = cls.BACKSLASH

		ld['SPECIAL'] = cls.SPECIAL
		ld['S'] = cls.S

		ld['WordNode'] = cls.WordNode
		ld['StringNode'] = cls.StringNode
		ld['InfixOPNode'] = cls.InfixOPNode
		ld['PrefixOPNode'] = cls.PrefixOPNode
		ld['TupleNode'] = cls.TupleNode

	def __init__(self, prefix_ops: list[OperatorInfo], ptable: list[PrecedenceLayer] | dict[int, PrecedenceLayer]):
		self._ptable: dict[int, PrecedenceLayer]
		if isinstance(ptable, list):
			self._ptable = {i: p for i, p in enumerate(ptable)}
		else:
			self._ptable = ptable.copy()

		self._prefix_ops: list[OperatorInfo] = prefix_ops.copy()

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
		self._op_symbols = set(symbols)
		self._lexer = Lexer(symbols)

		self._infix_table: dict[str, Operator] = {op_info.symbol: op_info.op for op_info in chain.from_iterable(self._ptable.values())}
		self._infix_precedence_table: dict[str, int] = {op_info.symbol: precedence for precedence, layer in self._ptable.items() for op_info in layer}
		self._infix_asso_table: dict[str, Associability] = {op_info.symbol: layer.asso for precedence, layer in self._ptable.items() for op_info in layer}

		self._prefix_table: dict[str, Operator] = {op_info.symbol: op_info.op for op_info in self._prefix_ops}

	@staticmethod
	def pop_prefix(op_stack, total_stack):
		while len(op_stack) > 0 and op_stack[-1]._is_prefix_op:
			total_stack.append(op_stack.pop())

	def parse(self, s: str) -> TreeNodeType:
		self._constant_injure(locals())

		tokens = self._lexer.tokenize(s)
		status = S.INITIAL

		op_stack, total_stack = [], []

		for token in tokens:
			# Symbol: should be an operator
			# Word: may be operator or others...
			is_op, is_special = False, False
			if token in self._op_symbols:
				is_op = True
				if token in SPECIAL:
					is_special = True
			is_str = self._lexer.is_string(token)

			match status:
				case S.INITIAL | S.WAIT_LITERAL:
					if is_str:
						total_stack.append(StringNode(token[1:-1]))
						self.pop_prefix(op_stack, total_stack)
						status = S.WAIT_INFIX
					elif is_special:
						if token == LP:
							op_stack.append(ParenthesesNode(token)) # Put token is not needed
							status = S.WAIT_LITERAL
						else:
							raise ValueError(f'Unwanted special token {token} when waiting for literals')
					elif is_op:
						# Allow prefix operator
						if token in self._prefix_table:
							op_stack.append(PrefixOPNode(token))
							status = S.WAIT_LITERAL
						else:
							raise ValueError(f'Unwanted infix operator {token} when waiting for literals')
					else:
						total_stack.append(WordNode(token))
						self.pop_prefix(op_stack, total_stack)
						status = S.WAIT_INFIX
				case S.WAIT_INFIX:
					if is_special:
						...
					elif is_op:
						...
					else:
						raise ValueError(f'Unwanted literal {token} when waiting for infix operators')

		match status:
			case S.INITIAL:
				raise ValueError('No valid input string to parse')

		... # Pop all op in stacks
		... # Connect everything in total_stack
