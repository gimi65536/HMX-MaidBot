from collections.abc import Iterable
from pyparsing import *

class StringArgumentParser:
	'''
	This parser parses a long argument string like 'a bb "c d" e"f" "g\\"h"'
	into ['a', 'bb', 'c d', 'e', 'f', 'g"h'].
	'''
	parser = QuotedString(quote_char = '"', esc_char = '\\') | Regex(r'[^\s\"]+')

	@classmethod
	def pick(cls, s: str):
		return sum(cls.parser.search_string(s), ParseResults()).as_list()

	@staticmethod
	def rebuild(ss: Iterable[str]):
		f = lambda s: s.replace('"', '\\\"')
		l = [f'''"{f(i)}"''' for i in ss]
		return ' '.join(l)

__all__ = ('StringArgumentParser', )
