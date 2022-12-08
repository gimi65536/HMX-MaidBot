from collections.abc import Callable, Mapping
from sympy import Expr, simplify
from typing import Any, Generic, TypeVar, Union

class TreeNodeType:
	def eval(self, mapping: Mapping['Var', 'LValue']) -> 'Value':
		raise NotImplementedError

	def apply_var(self, f: Callable[['Var'], Any]):
		raise NotImplementedError

class Value:
	_is_constant: bool = False
	_is_lvalue: bool = False

	@property
	def is_constant(self):
		return self._is_constant

	@property
	def is_lvalue(self):
		return self._is_lvalue

class Var(TreeNodeType):
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

ConstType = TypeVar('ConstType', Expr, bool, str)

class Constant(TreeNodeType, Value, Generic[ConstType]):
	_is_number: bool
	_is_bool: bool
	_is_str: bool

	_is_dummy: bool = False

	_is_constant = True

	@classmethod
	def create_dummy(cls, dummy_value: ConstType):
		result = cls(dummy_value)
		result._is_dummy = True
		return result

	def with_dummy(self):
		if self.is_dummy:
			return self

		return type(self).create_dummy(self._value)

	def without_dummy(self):
		if not self.is_dummy:
			return self

		return type(self)(self._value)

	def __init__(self, value: ConstType):
		self._value = value

	@property
	def value(self) -> ConstType:
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

	@property
	def is_dummy(self) -> bool:
		return self._is_dummy

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

class LValue(Value):
	_is_lvalue = True

	def __init__(self, var: Var, const: Constant, bookkeeping: dict['LValue', tuple[Constant, Constant]] = {}):
		self._var = var
		self._content = const
		self._bookkeeping = bookkeeping

	@property
	def var(self):
		return self._var

	@property
	def content(self) -> Constant:
		return self._content

	@content.setter
	def content(self, const: Constant):
		if self in self._bookkeeping:
			self._content = const
			ori = self._bookkeeping[self][0]
			if ori == const:
				self._bookkeeping.pop(self)
			else:
				self._bookkeeping[self] = (ori, const)
		else:
			ori = self._content
			if ori != const:
				self._content = const
				self._bookkeeping[self] = (ori, const)

class Operator(TreeNodeType):
	# An immutable type
	ary: int
	_operands: list[TreeNodeType]

	def __init__(self, *args: TreeNodeType):
		if len(args) != self.ary:
			raise ValueError('Unmatched numbers of operands.')

		self._operands = args

	def eval(self, mapping):
		raise NotImplementedError

	def eval_operand(self, i: int, mapping: Mapping[Var, LValue]) -> Value:
		return self._operands[i].eval(mapping)

	def eval_operands(self, mapping: Mapping[Var, LValue]) -> list[Value]:
		return [o.eval(mapping) for o in self._operands]

	def eval_and_extract_constant(self, i: int, mapping: Mapping[Var, LValue]) -> Constant:
		return self.extract_constant(self.eval_operand(i, mapping))

	def eval_and_extract_constants(self, mapping: Mapping[Var, LValue]) -> list[Constant]:
		return self.extract_constants(*self.eval_operands(mapping))

	def apply_var(self, f):
		for o in self._operands:
			o.apply_var(f)

	@staticmethod
	def extract_constant(value: Value) -> Constant:
		if isinstance(v, Constant):
			return v
		else:
			return v.content

	@classmethod
	def extract_constants(cls, *args: Value) -> list[Constant]:
		return [cls.extract_constant(v) for v in args]
