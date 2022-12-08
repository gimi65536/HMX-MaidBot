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
			OperatorInfo(op_basic.MultipleOperator, '*'),
			OperatorInfo(op_basic.DivideOperator, '/'),
			OperatorInfo(op_basic.IntegerDivideOperator, '//'),
			OperatorInfo(op_basic.ModuloOperator, '%'),
		),
		20: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(op_basic.PlusOperator, '+'),
			OperatorInfo(op_basic.MinusOperator, '-'),
			OperatorInfo(op_basic.ConcatOperator, '.'),
		),
		70: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(op_basic.LessOperator, '<'),
			OperatorInfo(op_basic.LeOperator, '<='),
			OperatorInfo(op_basic.GreaterOperator, '>'),
			OperatorInfo(op_basic.GeOperator, '>='),
		),
		80: PrecedenceLayer(Associability.LEFT,
			OperatorInfo(op_basic.EqualOperator, '=='),
			OperatorInfo(op_basic.NonequalOperator, '!='),
		),
		110: PrecedenceLayer(Associability.RIGHT,
			OperatorInfo(op_basic.AndOperator, '&&'),
			OperatorInfo(op_basic.OrOperator, '||'),
			OperatorInfo(op_basic.ImplOperator, '->'),
			OperatorInfo(op_basic.XorOperator, '^'),
			OperatorInfo(op_basic.IffOperator, '<->'),
		),
	}

	default_prefix_ops = [
		OperatorInfo(op_basic.PositiveOperator, '+'),
		OperatorInfo(op_basic.NegativeOperator, '-'),
		OperatorInfo(op_basic.NotOperator, '~'),
	]

	default_postfix_ops = [
	]

	return Parser(default_prefix_ops, default_postfix_ops, default_precedence_table)
