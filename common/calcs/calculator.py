from __future__ import annotations
from .exceptions import *
from .op_basic import *
from .types import Constant, Operator, TreeNodeType, Var
from collections import Counter
from enum import Enum
from itertools import chain
from sympy import Float, I, Rational
from typing import cast, Optional
import random
import re

class Associability(Enum):
	NOTCARE = 0
	LEFT = 1
	RIGHT = 2

class OperatorInfo:
	@classmethod
	def factory(cls, op: type[Operator], *symbols: str) -> list[OperatorInfo]:
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
		if any(i > 1 for i in c.values()):
			raise ValueError('Two operators with the same symbol in the same precedence!')
		if any(o.ary != 2 for o in ops):
			raise ValueError(f'All operators should be binary')

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

class Token:
	_is_string_const: bool
	_is_symbol: bool

	def __init__(self, s: str, position: int):
		self._s = s
		self._p = position

	@property
	def string(self) -> str:
		return self._s

	@property
	def position(self) -> int:
		return self._p

	def __str__(self):
		return self._s

	@property
	def is_string_const(self):
		return self._is_string_const

	@property
	def is_symbol(self):
		return self._is_symbol

class WordToken(Token):
	_is_string_const = False
	_is_symbol = False

class StringToken(Token):
	_is_string_const = True
	_is_symbol = False

class SymbolToken(Token):
	_is_string_const = False
	_is_symbol = True

class Lexer:
	SQ = "'"
	DQ = '"'
	BACKSLASH = '\\'
	space_re: re.Pattern[str] = re.compile(r'\s', re.ASCII)
	word_re: Optional[re.Pattern[str]] = re.compile(r'\w|[^\x00-\x7f]', re.ASCII)
	symbol_re: Optional[re.Pattern[str]] = None
	assert not(word_re is None and symbol_re is None)

	class S(Enum):
		SYMBOL = 0
		WORD = 1
		INQUOTE = 2
		INQUOTE_ESCAPE = 3

	def full_word(self, s: str) -> bool:
		# Pre-condition: no spaces
		if self.word_re is not None:
			return all(self.word_re.match(c) for c in s)
		else:
			return not any(self.symbol_re.match(c) for c in s)

	def full_symbol(self, s: str) -> bool:
		# Pre-condition: no spaces
		if self.symbol_re is not None:
			return all(self.symbol_re.match(c) for c in s)
		else:
			return not any(self.word_re.match(c) for c in s)

	def __init__(self,
		op_symbols: list[str],
		word_re: Optional[re.Pattern[str]] = None,
		symbol_re: Optional[re.Pattern[str]] = None,
		space_re: Optional[re.Pattern[str]] = None, **kwargs):

		# Lexer constant check
		SQ = kwargs.pop('SQ', Lexer.SQ)
		DQ = kwargs.pop('DQ', Lexer.DQ)
		BACKSLASH = kwargs.pop('BACKSLASH', Lexer.BACKSLASH)

		if len(SQ) != 1:
			raise LexerConstructError('Length of SQ should be 1')
		if len(DQ) != 1:
			raise LexerConstructError('Length of DQ should be 1')
		if len(BACKSLASH) != 1:
			raise LexerConstructError('Length of BACKSLASH should be 1')

		self.SQ = SQ
		self.DQ = DQ
		self.BACKSLASH = BACKSLASH

		# All special constants for the lexer
		self.SPECIAL = SQ + DQ # Backslash is "not special enough"
		self._special_re = re.compile(f'[{re.escape(self.SPECIAL)}]')

		if word_re is None and symbol_re is None:
			self.word_re = Lexer.word_re
			self.symbol_re = None
		elif word_re is not None:
			self.word_re = word_re
			self.symbol_re = None
		else:
			self.word_re = None
			self.symbol_re = symbol_re

		if space_re is not None:
			self.space_re = space_re

		ss = []
		for symbol in op_symbols:
			if len(symbol) == 0:
				raise LexerConstructError('Empty operators are disallowed')
			if self.space_re.search(symbol):
				raise LexerConstructError('Operators with space characters are disallowed')
			if self._special_re.search(symbol):
				raise LexerConstructError(f'Operator cannot includes the following symbols (reserved for the lexer): "{self.SPECIAL}"')

			if self.full_word(symbol):
				continue
			elif self.full_symbol(symbol):
				ss.append(symbol)
			else:
				raise LexerConstructError('Operators mixed with symbols and words are disallowed')

		self._parse_symbols = set(ss)
		self._find_cache: dict[str, Optional[list[SymbolToken]]] = {'': []}

	def _find_without_position(self, symbols: str) -> Optional[list[SymbolToken]]:
		if symbols in self._find_cache:
			return self._find_cache[symbols]

		for i in range(len(symbols), 0, -1):
			prefix = symbols[:i]
			if prefix not in self._parse_symbols:
				continue

			sub_result = self._find_without_position(symbols[i:])
			if sub_result is None:
				continue
			sub_result = [SymbolToken(token.string, token.position + i) for token in sub_result]

			self._find_cache[symbols] = [SymbolToken(prefix, 0), *sub_result]
			return self._find_cache[symbols]

		self._find_cache[symbols] = None
		return None

	def _find(self, symbols: str, position: int) -> Optional[list[SymbolToken]]:
		result = self._find_without_position(symbols)
		if result is None:
			return None

		return [SymbolToken(token.string, token.position + position) for token in result]

	def is_word(self, c):
		# Pre-condition: no spaces
		if self.word_re is not None:
			return self.word_re.match(c)
		else:
			return self.symbol_re.match(c)

	def tokenize(self, s: str) -> list[Token]:
		SQ = self.SQ
		DQ = self.DQ
		BACKSLASH = self.BACKSLASH
		S = self.S

		# First step split
		first: list[tuple[int, str]] = []
		status = S.SYMBOL
		keep, keep_from, quote = '', 0, DQ
		for i, c in enumerate(s, 1):
			match status:
				case S.INQUOTE_ESCAPE:
					# Only escape that \? = ?
					# keep_from won't update
					keep += c
					status = S.INQUOTE
				case S.INQUOTE:
					# keep_from won't update
					if quote == c:
						first.append((keep_from, keep + c))
						keep = ''
						status = S.SYMBOL
					elif quote == BACKSLASH:
						status = S.INQUOTE_ESCAPE
					else:
						keep += c
				case S.SYMBOL:
					if self.space_re.match(c):
						if len(keep) > 0:
							first.append((keep_from, keep))
						keep = ''
					elif self.is_word(c):
						if len(keep) > 0:
							first.append((keep_from, keep))
						keep = c
						keep_from = i
						status = S.WORD
					elif c == SQ or c == DQ:
						if len(keep) > 0:
							first.append((keep_from, keep))
						keep = c
						keep_from = i
						quote = c
						status = S.INQUOTE
					else:
						if len(keep) == 0:
							keep_from = i
						keep += c
				case S.WORD:
					if self.space_re.match(c):
						if len(keep) > 0:
							first.append((keep_from, keep))
						keep = ''
					elif self.is_word(c):
						if len(keep) == 0:
							keep_from = i
						keep += c
					elif c == SQ or c == DQ:
						if len(keep) > 0:
							first.append((keep_from, keep))
						keep = c
						keep_from = i
						quote = c
						status = S.INQUOTE
					else:
						if len(keep) > 0:
							first.append((keep_from, keep))
						keep = c
						keep_from = i
						status = S.SYMBOL

		if status == S.INQUOTE or status == S.INQUOTE_ESCAPE:
			raise TokenizeError(keep_from, 'Quote not closed')
		if len(keep) > 0:
			first.append((keep_from, keep))

		result: list[Token] = []
		for i, token in first:
			if token.startswith(SQ) or token.startswith(DQ):
				result.append(StringToken(token[1:-1], i))
				continue

			if self.full_word(token):
				result.append(WordToken(token, i))
				continue

			find = self._find(token, i)
			if find is None:
				raise TokenizeError(token.position, f'Tokenize error with the symbols "{token}"')
			result.extend(find)

		return result

class Parser:
	LP = '('
	RP = ')'
	COMMA = ',' # Acts like a binary infix operator with the lowest prec and left-asso
	imagine_re: re.Pattern[str] = re.compile(r'^(.*)[IiJj]$')
	wildcard_re: re.Pattern[str] = re.compile(r'_')

	class S(Enum):
		INITIAL = 0
		WAIT_LITERAL = 1
		WAIT_INFIX = 2

	class SyntaxTreeNode:
		def __init__(self, content: str, position: int):
			self.content = content
			self.position = position

		def __str__(self):
			return str(self.content)

		_is_word: bool = False
		_is_str: bool = False
		_is_op: bool = False
		_is_prefix_op: bool = False
		_is_infix_op: bool = False
		_is_postfix_op: bool = False
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
		def is_infix_op(self):
			return self._is_infix_op

		@property
		def is_postfix_op(self):
			return self._is_postfix_op

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

		def __init__(self, symbol: str, position: int, operand: Optional[SyntaxTreeNode] = None):
			# operand is None in op_stack, not None in total_stack
			super().__init__(symbol, position)
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
		_is_infix_op = True

	class PrefixOPNode(OpNode):
		_is_prefix_op = True

	# Not in op_stack
	class PostfixOPNode(OpNode):
		_is_postfix_op = True

	# Not in total_stack
	class CommaNode(SyntaxTreeNode):
		_is_comma = True

	# Not in total_stack
	class ParenthesesNode(SyntaxTreeNode):
		_is_parentheses = True

	class TupleNode(SyntaxTreeNode):
		_is_tuple = True

		def __init__(self, t: tuple[SyntaxTreeNode, ...], position: int):
			self.content = t
			self.position = position

	def __init__(self,
		prefix_ops: list[OperatorInfo],
		postfix_ops: list[OperatorInfo],
		ptable: list[PrecedenceLayer] | dict[int, PrecedenceLayer],
		imagine_re: Optional[re.Pattern[str]] = None,
		wildcard_re: Optional[re.Pattern[str]] = None, **kwargs):

		# Parser constant check
		LP = kwargs.pop('LP', Parser.LP)
		RP = kwargs.pop('RP', Parser.RP)
		COMMA = kwargs.pop('COMMA', Parser.COMMA)

		if len(LP) != 1:
			raise ParserConstructError('Length of LP should be 1')
		if len(RP) != 1:
			raise ParserConstructError('Length of RP should be 1')
		if len(COMMA) != 1:
			raise ParserConstructError('Length of COMMA should be 1')

		self.LP = LP
		self.RP = RP
		self.COMMA = COMMA

		# All special constants for the parser
		self.SPECIAL = LP + RP + COMMA
		self._special_re = re.compile(f'[{re.escape(self.SPECIAL)}]')

		# Pass arguments

		self._ptable: dict[int, PrecedenceLayer]
		if isinstance(ptable, list):
			self._ptable = {i: p for i, p in enumerate(ptable)}
		else:
			self._ptable = ptable.copy()

		self._prefix_ops: list[OperatorInfo] = prefix_ops.copy()
		self._postfix_ops: list[OperatorInfo] = postfix_ops.copy()

		if imagine_re is not None:
			self.imagine_re = imagine_re
		if wildcard_re is not None:
			self.wildcard_re = wildcard_re

		# Build tables

		# Infix operator
		self._infix_table: dict[str, Operator] = {op_info.symbol: op_info.op for op_info in chain.from_iterable(self._ptable.values())}
		self._infix_precedence_table: dict[str, int] = {op_info.symbol: precedence for precedence, layer in self._ptable.items() for op_info in layer}
		self._infix_asso_table: dict[str, Associability] = {op_info.symbol: layer.asso for precedence, layer in self._ptable.items() for op_info in layer}

		for symbol, op in self._infix_table.items():
			if op.ary != 2:
				raise ParserConstructError(f'Infix operator {symbol} is {op.ary}-ary, binary is needed for infix operators')

		# Prefix operator can be overloaded... like functions
		self._prefix_table: dict[str, dict[int, Operator]] = {}
		for prefix_op in self._prefix_ops:
			symbol, ary, op = prefix_op.symbol, prefix_op.ary, prefix_op.op
			if symbol not in self._prefix_table:
				self._prefix_table[symbol] = {}

			if ary in self._prefix_table[symbol]:
				raise ParserConstructError(f'Two prefix operators with the same symbol and the same ary!')

			self._prefix_table[symbol][ary] = op

		# Postfix operator can be overloaded...
		# However I don't think it is a good idea to have a prefix operator other than unary.
		self._postfix_table: dict[str, dict[int, Operator]] = {}
		for postfix_op in self._postfix_ops:
			symbol, ary, op = postfix_op.symbol, postfix_op.ary, postfix_op.op
			if symbol in self._infix_table:
				raise ParserConstructError(f'The symbol {symbol} is both infix and postfix, which is disallowed')
			if symbol not in self._postfix_table:
				self._postfix_table[symbol] = {}

			if ary in self._postfix_table[symbol]:
				raise ParserConstructError(f'Two postfix operators with the same symbol and the same ary!')

			self._postfix_table[symbol][ary] = op

		infix_symbols = list(chain.from_iterable(layer.symbols for layer in self._ptable.values()))
		for symbol, i in Counter(infix_symbols).items():
			if i > 1:
				raise ParserConstructError(f'Two infix operators with the same symbol {symbol}')

		symbols = infix_symbols + [prefix_op.symbol for prefix_op in self._prefix_ops] + [postfix_op.symbol for postfix_op in self._postfix_ops]
		# Sanitize
		for symbol in symbols:
			if self._special_re.search(symbol):
				raise ParserConstructError(f'Operator cannot includes the following symbols (reserved for the parser): "{self.SPECIAL}"')

		symbols.extend(self.SPECIAL)
		self._op_symbols = set(symbols)

		# Build the lexer
		self._lexer = Lexer(symbols, **kwargs)

	def _pop_prefix(self, op_stack, total_stack):
		while len(op_stack) > 0 and op_stack[-1]._is_prefix_op:
			self._merge(op_stack.pop(), total_stack)

	def _merge(self, op_node, total_stack):
		InfixOPNode = self.InfixOPNode
		PrefixOPNode = self.PrefixOPNode
		PostfixOPNode = self.PostfixOPNode
		TupleNode = self.TupleNode

		if not op_node.is_op and not op_node.is_comma:
			raise ParseError(op_node.position, 'Unknown error caused by non-operators in op_stack')

		if op_node.is_prefix_op:
			if len(total_stack) == 0:
				raise ParseError(op_node.position, f'Prefix operator {op_node.content} encountered no operand')
			node = total_stack.pop()
			total_stack.append(PrefixOPNode(op_node.content, op_node.position, node))
		elif op_node.is_postfix_op:
			if len(total_stack) == 0:
				raise ParseError(op_node.position, f'Postfix operator {op_node.content} encountered no operand')
			node = total_stack.pop()
			total_stack.append(PostfixOPNode(op_node.content, node.position, node))
		else:
			# Infix (op or comma)
			if len(total_stack) < 2:
				if op_node.is_op:
					raise ParseError(op_node.position, f'Infix operator {op_node.content} encountered less than 2 operands')
				else:
					raise ParseError(op_node.position, f'Comma {op_node.content} encountered less than 2 operands')
			n2, n1 = total_stack.pop(), total_stack.pop()

			if op_node.is_op:
				total_stack.append(InfixOPNode(op_node.content, n1.position, TupleNode((n1, n2), n1.position)))
			else:
				if n2.is_tuple:
					raise ParseError(n2.position, f'Invalid nested tuple {n2.content}')
				t = ()
				if n1.is_tuple:
					t = n1.content + (n2, )
				else:
					t = (n1, n2)
				total_stack.append(TupleNode(t, n1.position))

	def str_to_const(self, s: str) -> Constant | Var:
		# This method applies on a token in the parser
		# That is, only a "word" should appear here
		# Boolean parse
		if s == 'TRUE' or s == 'True' or s == 'true':
			return BooleanConstant(True)
		elif s == 'FALSE' or s == 'False' or s == 'false':
			return BooleanConstant(False)

		if self.wildcard_re.fullmatch(s):
			return NumberConstant.create_dummy(Float(random.random()))

		# Math constant parse
		# pi...

		# Imaginary number parse
		if (m := self.imagine_re.fullmatch(s)):
			# May be imaginary number
			r = m.group(1)
			if len(r) == 0:
				return NumberConstant(I)
			try:
				n = Rational(r)
				return NumberConstant(n * I)
			except:
				pass

		# Rational number parse
		try:
			# Every real number can be given must be rational
			n = Rational(s)
			return NumberConstant(n)
		except:
			pass

		return Var(s)

	def _to_semantic_tree(self, node: SyntaxTreeNode) -> TreeNodeType:
		OpNode = self.OpNode
		TupleNode = self.TupleNode

		if node.is_str:
			return StringConstant(node.content)
		elif node.is_word:
			return self.str_to_const(node.content)
		elif node.is_op:
			node = cast(OpNode, node)
			operand = node.operand
			if operand is None:
				raise ParseError(node.position, 'Unknown error: Operator with no operand')

			if node.is_prefix_op or node.is_postfix_op:
				# prefix
				ary: int
				operands_node: tuple[SyntaxTreeNode, ...]
				if not operand.is_tuple:
					ary = 1
					operands_node = (operand, )
				else:
					cast(TupleNode, operand)
					operands_node = operand.content
					ary = len(operands_node)

				if node.is_prefix_op:
					if ary not in self._prefix_table[node.content]:
						raise ParseError(node.position, f'Prefix operator {node.content} is not {ary}-ary')

					operands = [self._to_semantic_tree(subn) for subn in operands_node]
					op = self._prefix_table[node.content][ary]
				else:
					if ary not in self._postfix_table[node.content]:
						raise ParseError(node.position, f'Postfix operator {node.content} is not {ary}-ary')

					operands = [self._to_semantic_tree(subn) for subn in operands_node]
					op = self._postfix_table[node.content][ary]
			else:
				# infix
				if not operand.is_tuple:
					raise ParseError(node.position, 'Unknown error: Infix operator has only one operand')

				cast(TupleNode, operand)
				t = operand.content
				if len(t) != 2:
					raise ParseError(node.position, f'Unknown error: Infix operator has {len(t)} operand')

				operands = [self._to_semantic_tree(subn) for subn in t]
				op = self._infix_table[node.content]

			return op(*operands)
		else:
			raise ParseError(node.position, f'Unknown error: Invalid for semantic trees {type(node)}: {node}')

	def parse(self, s: str) -> TreeNodeType:
		LP= self.LP
		RP = self.RP
		COMMA = self.COMMA
		SPECIAL = self.SPECIAL
		S = self.S
		WordNode = self.WordNode
		StringNode = self.StringNode
		InfixOPNode = self.InfixOPNode
		PrefixOPNode = self.PrefixOPNode
		PostfixOPNode = self.PostfixOPNode
		CommaNode = self.CommaNode
		ParenthesesNode = self.ParenthesesNode
		TupleNode = self.TupleNode

		tokens = self._lexer.tokenize(s)
		status = S.INITIAL

		op_stack, total_stack = [], []

		for token in tokens:
			# Symbol: should be an operator
			# Word: may be operator or others...
			is_op, is_special, is_str = False, False, False
			if token.is_symbol:
				is_op = True
				if token.string in SPECIAL:
					is_special = True
			elif token.is_string_const:
				is_str = True
			else:
				if token.string in self._op_symbols:
					is_op = True

			match status:
				case S.INITIAL | S.WAIT_LITERAL:
					if is_str:
						total_stack.append(StringNode(token.string, token.position))
						self._pop_prefix(op_stack, total_stack)
						status = S.WAIT_INFIX
					elif is_special:
						if token.string == LP:
							op_stack.append(ParenthesesNode(token.string, token.position)) # Put token is not needed
							status = S.WAIT_LITERAL
							continue
						elif token.string == RP:
							# To accept "()" or "(... , )"
							if len(op_stack) > 0:
								peek = op_stack[-1]
								if peek.is_parentheses:
									# ()
									lp_node = op_stack.pop()
									total_stack.append(TupleNode((), lp_node.position))
									status = S.WAIT_INFIX
									continue
								elif peek.is_comma:
									# (... , )
									op_stack.pop()
									# Because COMMA will pop all other operators in parentheses,
									# the next element in the stack should be the parenthesis.
									if len(op_stack) == 0 or not op_stack[-1].is_parentheses:
										raise ParseError(peek.position, 'Unknown error: Not merged expressions before comma')
									op_stack.pop()
									status = S.WAIT_INFIX
									continue

						raise ParseError(token.position, f'Unwanted special token {token} when waiting for literals')
					elif is_op:
						# Allow prefix operator
						if token.string in self._prefix_table:
							op_stack.append(PrefixOPNode(token.string, token.position))
							status = S.WAIT_LITERAL
						else:
							raise ParseError(token.position, f'Unwanted infix operator {token} when waiting for literals')
					else:
						total_stack.append(WordNode(token.string, token.position))
						self._pop_prefix(op_stack, total_stack)
						status = S.WAIT_INFIX
				case S.WAIT_INFIX:
					if is_special:
						if token.string == RP:
							# Close "normal" parentheses (x, y, ..., z)
							while len(op_stack) > 0 and not op_stack[-1].is_parentheses:
								self._merge(op_stack.pop(), total_stack)

							if len(op_stack) == 0:
								raise ParseError(token.position, 'Non-close parentheses')
							lp_node = op_stack.pop()
							# Override the tuple position to the LP position
							total_stack[-1].position = lp_node.position

							status = S.WAIT_INFIX
						elif token.string == COMMA:
							while len(op_stack) > 0 and not op_stack[-1].is_parentheses:
								self._merge(op_stack.pop(), total_stack)

							if len(op_stack) == 0:
								raise ParseError(token.position, 'Comma outsides parentheses')
							op_stack.append(CommaNode(token.string, token.position)) # Put token is not needed

							status = S.WAIT_LITERAL
						else:
							raise ParseError(token.position, f'Unwanted special token {token} when waiting for infix operators')
					elif is_op:
						# Allow infix and postfix operator
						if token.string in self._infix_table:
							precedence = self._infix_precedence_table[token.string]
							asso = self._infix_asso_table[token.string]

							while len(op_stack) > 0:
								node = op_stack[-1]
								if node.is_infix_op:
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

							op_stack.append(InfixOPNode(token.string, token.position))
							status = S.WAIT_LITERAL
						elif token.string in self._postfix_table:
							self._merge(PostfixOPNode(token.string, token.position), total_stack)
						else:
							raise ParseError(token.position, f'Unwanted prefix operator {token} when waiting for infix operators')
					else:
						raise ParseError(token.position, f'Unwanted literal {token} when waiting for infix operators')

		match status:
			case S.INITIAL:
				raise ParseError(1, 'No valid input string to parse')

		while len(op_stack) > 0 and op_stack[-1].is_op:
			self._merge(op_stack.pop(), total_stack)

		if len(op_stack) > 0:
			op_node = op_stack[-1]
			raise ParseError(op_node.position, f'Unresolved operator {op_node.content} in op_stack')

		if len(total_stack) != 1:
			raise ParseError(0, f'Unknown status of total_stack: {total_stack}')

		node = total_stack[0]

		if node.is_tuple:
			raise ParseError(node.position, 'Topmost element is tuple')

		return self._to_semantic_tree(node)
