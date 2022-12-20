from collections import Counter
from collections.abc import Mapping
from typing import TypeVar

KT = TypeVar('KT')
VT = TypeVar('VT')

# This is a remake of the built-in type MappingProxyType.
# It is not recommended to use this directly since there
# is the built-in version and that performs better.
class _MappingProxyType(Mapping[KT, VT]):
	_d: Mapping[KT, VT]

	def __init__(self, mapping: Mapping):
		self._d = mapping

	def __contains__(self, item):
		return self._d.__contains__(item)

	def __getitem__(self, key):
		return self._d.__getitem__(key)

	def __iter__(self):
		return self._d.__iter__()

	def __len__(self):
		return self._d.__len__()

	def copy(self):
		return {k: v for k, v in self.items()}

	def get(self, key, default = None):
		return self._d.get(key, default)

	def items(self):
		return self._d.items()

	def keys(self):
		return self._d.keys()

	def values(self):
		return self._d.values()

	def __reversed__(self):
		return reversed(self.keys())

class CounterProxyType(_MappingProxyType[KT, int]):
	_d: Counter

	def __init__(self, counter: Counter):
		super().__init__(counter)

	def elements(self):
		return self._d.elements()

	def most_common(self, n = None):
		return self._d.most_common(n)

	def total(self):
		return self._d.total()
