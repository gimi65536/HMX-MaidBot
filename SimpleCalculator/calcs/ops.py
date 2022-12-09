from .types import Operator

class NullaryOperator(Operator):
	ary = 0

class UnaryOperator(Operator):
	ary = 1

class BinaryOperator(Operator):
	ary = 2

class TernaryOperator(Operator):
	ary = 3