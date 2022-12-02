from decimal import Decimal
from fractions import Fraction
from .types import Constant, NumType

class IntegerConstant(Constant[int]):
	t = int

class FloatConstant(Constant[float]):
	t = float

class ComplexConstant(Constant[complex]):
	t = complex

class DecimalConstant(Constant[Decimal]):
	t = Decimal

class FractionConstant(Constant[Fraction]):
	t = Fraction

class BooleanConstant(Constant[bool]):
	t = bool

class StringConstant(Constant[str]):
	t = str

type_constant: dict[NumType, Constant] = {
	int: IntegerConstant,
	float: FloatConstant,
	complex: ComplexConstant,
	Decimal: DecimalConstant,
	Fraction: FractionConstant,
	bool: BooleanConstant,
	str: StringConstant
}

__all__ = (
	IntegerConstant,
	FloatConstant,
	ComplexConstant,
	DecimalConstant,
	FractionConstant,
	BooleanConstant,
	StringConstant,
	type_constant
)