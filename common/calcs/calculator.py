from .ops_basic import *
from .types import Operator, TreeNodeType
from collections import Counter
from enum import Enum
from itertools import chain
from typing import cast, Optional
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

		def __str__(self):
			return str(self.content)

		_is_word: bool = False
		_is_str: bool = False
		_is_op: bool = False
		_is_prefix_op: bool = False
		_is_comma: bool = False
		_is_parentheses: bool = False
		_is_tuple: bool = False

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
		def is_comma(self):
			return self._is_comma

		@property
		def is_parentheses(self):
			return self._is_parentheses

		@property
		def is_tuple(self):
			return self._is_tuple

	class WordNode(SyntaxTreeNode):
		_is_word = True

	class StringNode(SyntaxTreeNode):
		_is_word = True
		_is_str = True

	class OpNode(SyntaxTreeNode):
		_is_op = True

		def __init__(self, symbol: str, operand: Optional[SyntaxTreeNode] = None):
			# operand is None in op_stack, not None in total_stack
			super().__init__(symbol)
			self._operand = operand

		@property
		def operand(self) -> Optional[SyntaxTreeNode]:
			return self._operand

		def __str__(self):
			if self.operand is None:
				return super().__str__()

			if self.operand.is_tuple:
				return f'{self.operand}{super().__str__()}'
			else:
				return f'({self.operand}){super().__str__()}'

	class InfixOPNode(OpNode):
		_is_prefix_op = False

	class PrefixOPNode(OpNode):
		_is_prefix_op = True

	# Not in total_stack
	class CommaNode(SyntaxTreeNode):
		_is_comma = True

	# Not in total_stack
	class ParenthesesNode(SyntaxTreeNode):
		_is_parentheses = True

	class TupleNode(SyntaxTreeNode):
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
		ld['CommaNode'] = cls.CommaNode
		ld['ParenthesesNode'] = cls.ParenthesesNode
		ld['TupleNode'] = cls.TupleNode

	def __init__(self, prefix_ops: list[OperatorInfo], ptable: list[PrecedenceLayer] | dict[int, PrecedenceLayer]):
		self._ptable: dict[int, PrecedenceLayer]
		if isinstance(ptable, list):
			self._ptable = {i: p for i, p in enumerate(ptable)}
		else:
			self._ptable = ptable.copy()

		self._prefix_ops: list[OperatorInfo] = prefix_ops.copy()

		# Build tables

		self._infix_table: dict[str, Operator] = {op_info.symbol: op_info.op for op_info in chain.from_iterable(self._ptable.values())}
		self._infix_precedence_table: dict[str, int] = {op_info.symbol: precedence for precedence, layer in self._ptable.items() for op_info in layer}
		self._infix_asso_table: dict[str, Associability] = {op_info.symbol: layer.asso for precedence, layer in self._ptable.items() for op_info in layer}

		for symbol, op in self._infix_table.items():
			if op.ary != 2:
				raise ValueError(f'Infix operator {symbol} is {op.ary}-ary, binary is needed for infix operators')

		# Prefix operator can be overloaded... like functions
		self._prefix_table: dict[str, dict[int, Operator]] = {}
		for prefix_op in self._prefix_ops:
			symbol, ary, op = prefix_op.symbol, prefix_op.ary, prefix_ops.op
			if symbol not in self._prefix_table:
				self._prefix_table[symbol] = {}

			if ary in self._prefix_table[symbol]:
				raise ValueError(f'Two prefix operators with the same symbol and the same ary!')

			self._prefix_table[symbol][ary] = op

		# Build the lexer

		infix_symbols = list(chain.from_iterable(layer.symbols for layer in self._ptable.values()))
		for symbol, i in Counter(infix_symbols).items():
			if i > 1:
				raise ValueError(f'Two infix operators with the same symbol {symbol}')

		symbols = infix_symbols + [prefix_op.symbol for prefix_op in self._prefix_ops]
		# Sanitize
		for symbol in symbols:
			if self._special_re.search(symbol):
				raise ValueError(f'Operator cannot includes the following symbols: "{self._special}"')

		symbols.extend(self._special)
		self._op_symbols = set(symbols)
		self._lexer = Lexer(symbols)

	@staticmethod
	def pop_prefix(op_stack, total_stack):
		while len(op_stack) > 0 and op_stack[-1]._is_prefix_op:
			total_stack.append(op_stack.pop())

	def _merge(op_node, total_stack):
		if not op_node.is_op or not op_node.is_comma:
			raise ValueError('Unknown error caused by non-operators in op_stack')

		if op_node.is_prefix_op:
			if len(total_stack) == 0:
				raise ValueError(f'Prefix operator {op_node.content} encountered no operand')
			node = total_stack.pop()
			total_stack.append(PrefixOPNode(op_node.content, node))
		else:
			# Infix (op or comma)
			if len(total_stack) < 2:
				if op_node.is_op:
					raise ValueError(f'Infix operator {op_node.content} encountered less than 2 operands')
				else:
					raise ValueError(f'Comma {op_node.content} encountered less than 2 operands')
			n2, n1 = total_stack.pop(), total_stack.pop()

			if op_node.is_op:
				total_stack.append(InfixOPNode(op_node.content, TupleNode((n1, n2))))
			else:
				if n2.is_tuple:
					raise ValueError(f'Invalid nested tuple {n2.content}')
				t = ()
				if n1.is_tuple:
					t = n1.content + (n2, )
				else:
					t = (n1, n2)
				total_stack.append(TupleNode(t))

	def _to_semantic_tree(self, node: SyntaxTreeNode) -> TreeNodeType:
		if node.is_str:
			return StringConstant(node.content)
		elif node.is_word:
			...
		elif node.is_op:
			node = cast(OpNode, node)
			operand = node.operand
			if operand is None:
				raise ValueError('Unknown error: Operator with no operand')

			if node.is_prefix_op:
				# prefix
				ary: int
				operands_node: tuple[SyntaxTreeNode]
				if not operand.is_tuple:
					ary = 1
					operands_node = (operand, )
				else:
					cast(TupleNode, operand)
					operands_node = operand.content
					ary = len(operands_node)

				if ary not in self._prefix_table[node.content]:
					raise ValueError(f'Prefix operator {node.content} is not {ary}-ary')

				operands = [self._to_semantic_tree(subn) for subn in operands_node]
				op = self._prefix_table[node.content][ary]
			else:
				# infix
				if not operand.is_tuple:
					raise ValueError('Unknown error: Infix operator has only one operand')

				cast(TupleNode, operand)
				t = operand.content
				if len(t) != 2:
					raise ValueError(f'Unknown error: Infix operator has {len(t)} operand')

				operands = [self._to_semantic_tree(subn) for subn in t]
				op = self._infix_table[node.content]

			return op(*operands)
		else:
			raise ValueError(f'Unknown error: Invalid for semantic trees {type(node)}: {node}')

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
						if token == RP:
							# Close parentheses
							while len(op_stack) > 0 and not op_stack[-1].is_parentheses:
								self._merge(op_stack.pop(), total_stack)

							if len(op_stack) == 0:
								raise ValueError('Non-close parentheses')
							op_stack.pop()

							status = S.WAIT_INFIX
						elif token == COMMA:
							while len(op_stack) > 0 and not op_stack[-1].is_parentheses:
								self._merge(op_stack.pop(), total_stack)

							if len(op_stack) == 0:
								raise ValueError('Comma outsides parentheses')
							op_stack.append(CommaNode(token)) # Put token is not needed

							status = S.WAIT_LITERAL
						else:
							raise ValueError(f'Unwanted special token {token} when waiting for infix operators')
					elif is_op:
						# Allow infix operator
						if token in self._infix_table:
							precedence = self._infix_precedence_table[token]
							asso = self._infix_asso_table[token]

							while len(op_stack) > 0:
								node = op_stack[-1]
								if node.is_prefix_op:
									node_prec = self._infix_precedence_table[node.content]
									if precedence < node_prec:
										# Put the new operator
										break
									elif precedence > node_prec:
										self._merge(op_stack.pop(), total_stack)
									elif asso == Associability.LEFT:
										self._merge(op_stack.pop(), total_stack)
									else:
										break
								else:
									break

							op_stack.append(InfixOPNode(token))
							status = S.WAIT_LITERAL
						else:
							raise ValueError(f'Unwanted prefix operator {token} when waiting for infix operators')
					else:
						raise ValueError(f'Unwanted literal {token} when waiting for infix operators')

		match status:
			case S.INITIAL:
				raise ValueError('No valid input string to parse')

		while len(op_stack) > 0 and op_stack[-1].is_op:
			self._merge(op_stack.pop(), total_stack)

		if len(op_stack) > 0:
			raise ValueError(f'Unresolved operator {op_stack[-1].content} in op_stack')

		if len(total_stack) != 1:
			raise ValueError(f'Unknown status of total_stack: {total_stack}')

		node = total_stack[0]

		if node.is_tuple:
			raise ValueError(f'Topmost element is tuple')

		return self._to_semantic_tree(node)
