from numbers import Number
from typing import Any, Generic, TypeVar

class Var:
	_name: str
	_scope: Any # None for "weird" or "naive" variables

	def __init__(self, name, scope = None):
		self._name = name
		self._scope = scope

	@property
	def name(self) -> str:
		return self._name

	@property
	def scope(self) -> Any:
		return self._scope

	@scope.setter
	def scope(self, s: Any):
		self._scope = s

	def __eq__(self, other):
		if not isinstance(other, type(self)):
			return NotImplemented

		if self._name != other._name:
			return False

		if self._scope is None or other._scope is None:
			return True

		return self._scope == other._scope

	def __hash__(self):
		return hash(self._name)

NumType = TypeVar('NumType', bound = Number | bool | str)

class Constant(Generic[NumType]):
	numtype: type[NumType]

	def __init__(self, value: NumType):
		self._value = value

	@property
	def value(self):
		return self._value

	def cast(self, to_type: type['Constant']):
		return to_type(to_type.numtype(self._value))

	def __eq__(self, other):
		# Only True if the type is same
		if type(self) is not type(other):
			return NotImplemented

		return self._value == other._value

class LValue:
	def __init__(self, var: Var, value: Constant):
		self._var = var
		self._value = value

	@property
	def var(self):
		return self._var

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, value):
		self._value = value

@deprecated
class _COERTION:
	pass

@deprecated
class _CONTEXT_DEPENDENT:
	pass

@deprecated
class _INVALID:
	pass

Value: TypeAlias = Constant | LValue

SyntaxValue: TypeAlias = Constant | Var

#ValidResultType: TypeAlias = type[Constant] | _COERTION | _CONTEXT_DEPENDENT

#ResultType: TypeAlias = ValidResultType | _INVALID

class Operator:
	ary: int
	_operands: list[Value]

	def __init__(self, *args: Value):
		if len(args) != self.ary:
			raise ValueError('Unmatched numbers of operands.')

		self._operands = args

	def exec(self) -> Value:
		raise NotImplementedError

	def extract_constant(self) -> list[Constant]:
		result = []
		for o in self._operands:
			if isinstance(o, Constant):
				result.append(o)
			else:
				result.append(o.value)

		return result