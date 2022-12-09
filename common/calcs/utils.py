from .types import *
from collections.abc import Mapping

# Simply pick the firstly encountered variable.
def mapping_flatten(mapping: Mapping[Var, LValue]) -> Mapping[Var, LValue]:
	d = {}
	for v, lv in mapping.items():
		var = Var(v.name)
		if var in d:
			continue

		d[var] = lv

	return d
