from .types import Constant
from .numtypes import *

__all__ = ('coercion', )

# From A type to B type: Enlarger without loss information
# This relation is asymmetric
# String is a special case: every value can be casted to string implicitly
_coercion_relation: set[tuple[type[Constant], type[Constant]]] = set([
	(IntegerConstant, FloatConstant),
	(IntegerConstant, ComplexConstant),
	(IntegerConstant, DecimalConstant),
	(IntegerConstant, FractionConstant),
	(IntegerConstant, StringConstant),
	#
	(FloatConstant, ComplexConstant),
	(FloatConstant, DecimalConstant),
	(FloatConstant, FractionConstant),
	(FloatConstant, StringConstant),
	#
	(ComplexConstant, StringConstant),
	#
	(DecimalConstant, FractionConstant),
	(DecimalConstant, StringConstant),
	#
	(FractionConstant, StringConstant),
	#
	(BooleanConstant, IntegerConstant),
	(BooleanConstant, FloatConstant),
	(BooleanConstant, ComplexConstant),
	(BooleanConstant, DecimalConstant),
	(BooleanConstant, FractionConstant),
	(BooleanConstant, StringConstant)
])

def coercion(*cons: Constant, safe = True, coercion_relation = _coercion_relation) -> list[Constant]:
	if len(cons) == 0:
		return []

	cs = cons.copy()
	max_type = type(cs.pop(0))
	for c in cs:
		t: type[Constant] = type(c)
		if max_type is t:
			continue

		if (max_type, t) in coercion_relation:
			max_type = t
		elif (t, max_type) in coercion_relation:
			continue
		else:
			if safe:
				raise ValueError("Coertion error")
			else:
				# Somehow like JavaScript
				max_type = StringConstant

	result = []
	for c in cons:
		if max_type is c:
			result.append(c)
		else:
			result.append(c.cast(max_type))

	return result