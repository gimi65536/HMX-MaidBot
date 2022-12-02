from .types import _COERTION, _CONTEXT_DEPENDENT, _INVALID

# "If the coertion is allowed" then do coertion (the coertion relation is not always true)
COERTION = _COERTION()
CONTEXT_DEPENDENT = _CONTEXT_DEPENDENT()
INVALID = _INVALID()