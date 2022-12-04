from collections.abc import Callable
from sympy import Expr, simplify
from typing import Any, Generic, TypeVar, Union

# Interface class
class _Eval:
	def eval(self, mapping: Mapping['Var', 'LValue']) -> 'Value':
		raise NotImplementedError

	def apply_var(self, f: Callable[['Var'], Any]):
		raise NotImplementedError

class Var(_Eval):
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

	def eval(self, mapping):
		if self not in mapping:
			raise ValueError(f'Variable "{self._name}" is undefined')

		return mapping[self]

	def apply_var(self, f):
		f(self)

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

ConstType = TypeVar('ConstType', Expr | bool | str)

class Constant(_Eval, Generic[ConstType]):
	_is_number: bool
	_is_bool: bool
	_is_str: bool

	def __init__(self, value: ConstType):
		self._value = value

	@property
	def value(self):
		return self._value

	def eval(self, mapping):
		return self

	def apply_var(self, f):
		pass

	def __eq__(self, other):
		# Only True if the type is same
		if type(self) is not type(other):
			return NotImplemented

		return self._value == other._value

	def cast(self, to_type: type[Constant]):
		raise NotImplementedError

	def to_number(self) -> 'NumberConstant':
		return self.cast(NumberConstant)

	def to_bool(self) -> 'BooleanConstant':
		return self.cast(BooleanConstant)

	def to_str(self) -> 'StringConstant':
		return self.cast(StringConstant)

	@property
	def is_number(self) -> bool:
		return self._is_number

	@property
	def is_bool(self) -> bool:
		return self._is_bool

	@property
	def is_str(self) -> bool:
		return self._is_str

class NumberConstant(Constant[Expr]):
	_is_number = True
	_is_bool = False
	_is_str = False
	# The term "Number" in our program includes all complex numbers
	# So it is possible to have many "types" of SymPy data other than "SymPy.Number" 
	# such as I (ImaginaryUnit), 3*I (Mul), or 1+3*I (Add), they are not instances of SymPy.Number

	# In general that will cause problems if we don't restrict the Expr types used
	# Thus the value expressions should satisfy "is_number"
	def __init__(self, value):
		assert value.is_number
		super().__init__(value)

	def cast(self, to_type):
		match to_type:
			case NumberConstant:
				return self
			case BooleanConstant:
				return BooleanConstant(bool(self._value))
			case StringConstant:
				s, v = '', self._value
				if v.is_integer:
					s = str(int(v))
				elif v.is_Number:
					# Rational, Float
					s = str(v.evalf())
				elif v.is_irrational:
					# Other real numbers
					s = str(v.evalf())
				else:
					s = str(complex(v))

				return StringConstant(s)

class BooleanConstant(Constant[bool]):
	_is_number = False
	_is_bool = True
	_is_str = False

	def cast(self, to_type):
		match to_type:
			case NumberConstant:
				return NumberConstant(int(self._value))
			case BooleanConstant:
				return self
			case StringConstant:
				return StringConstant(str(self._value))

class StringConstant(Constant[str]):
	_is_number = False
	_is_bool = False
	_is_str = True

	def cast(self, to_type):
		match to_type:
			case NumberConstant:
				return NumberConstant(simplify(self._value))
			case BooleanConstant:
				return BooleanConstant(bool(self._value))
			case StringConstant:
				return self

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

Value: TypeAlias = Constant | LValue

SyntaxValue: TypeAlias = Constant | Var

TreeNodeType: TypeAlias = Union['Operator', Constant, Var]

#ValidResultType: TypeAlias = type[Constant] | _COERTION | _CONTEXT_DEPENDENT

#ResultType: TypeAlias = ValidResultType | _INVALID

class Operator(_Eval):
	# An immutable type
	ary: int
	_operands: list[TreeNodeType]

	def __init__(self, *args: TreeNodeType):
		if len(args) != self.ary:
			raise ValueError('Unmatched numbers of operands.')

		self._operands = args

	def eval(self, mapping):
		raise NotImplementedError

	def eval_operands(self, mapping: Mapping[Var, LValue]) -> list[Value]:
		result = []
		for o in self._operands:
			if isinstance(o, Operator):
				result.append(o.eval(mapping))
			elif isinstance(o, Var):
				raise ValueError('Unable to evaluate a pure variable.')
			else:
				result.append(o)

		return result

	def apply_var(self, f):
		for o in self._operands:
			o.apply_var(f)

	@staticmethod
	def extract_constant(*args: Value) -> list[Constant]:
		result = []
		for o in self._operands:
			if isinstance(o, Constant):
				result.append(o)
			else:
				result.append(o.value)

		return result