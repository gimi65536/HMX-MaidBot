from pyparsing import *

class StringArgumentParser:
	'''
	This parser parses a long argument string like 'a bb "c d" e"f" "g\\"h"'
	into ['a', 'bb', 'c d', 'e', 'f', 'g"h'].
	'''
	parser = ZeroOrMore(QuotedString(quote_char = '"', esc_char = '\\') | Regex(r'[^\s\"]+'))

	@classmethod
	def pick(cls, s: str):
		return sum(cls.parser.search_string(s))

__all__ = ('StringArgumentParser', )
