from .calculator import (
	Associability,
	OperatorInfo,
	Parser,
	PrecedenceLayer
)
from .types import *
from . import (
	op_assign,
	op_basic,
	op_num,
	op_rng,
	op_str,
	op_utils
)

def give_basic_parser():
	default_precedence_table = {
		10: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(MultipleOperator, '*'),
			OperatorInfo(DivideOperator, '/'),
			OperatorInfo(IntegerDivideOperator, '//'),
			OperatorInfo(ModuloOperator, '%'),
		),
		20: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(PlusOperator, '+'),
			OperatorInfo(MinusOperator, '-'),
			OperatorInfo(ConcatOperator, '.'),
		),
		70: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(LessOperator, '<'),
			OperatorInfo(LeOperator, '<='),
			OperatorInfo(GreaterOperator, '>'),
			OperatorInfo(GeOperator, '>='),
		),
		80: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(EqualOperator, '=='),
			OperatorInfo(NonequalOperator, '!='),
		),
		110: PrecedenceLayer(Associability.RIGHT,
			OperatorInfo(AndOperator, '&&'),
			OperatorInfo(OrOperator, '||'),
			OperatorInfo(ImplOperator, '->'),
			OperatorInfo(XorOperator, '^'),
			OperatorInfo(IffOperator, '<->'),
		),
	}

	default_prefix_ops = [
		OperatorInfo(PositiveOperator, '+'),
		OperatorInfo(NegativeOperator, '-'),
		OperatorInfo(NotOperator, '~'),
	]

	default_postfix_ops = [
	]

	return Parser(default_prefix_ops, default_postfix_ops, default_precedence_table)
