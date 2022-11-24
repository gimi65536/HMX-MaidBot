from collections import Counter
from types import MappingProxyType

class CounterProxyType(MappingProxyType):
	def __init__(self, counter: Counter):
		super().__init__(counter)
		# Seems that we cannot get the origin dict stored in MappingProxyType,
		# so we need to store it manually.
		self._c = counter

	def elements(self):
		return self._c.elements()

	def most_common(self, n = None):
		return self._c.most_common(n)

	def total(self):
		return self._c.total()
