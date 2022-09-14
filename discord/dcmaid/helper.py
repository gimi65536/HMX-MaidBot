'''
This module defines simple decorators to preserve the __doc__ information
as illustration in the command callback functions.
'''
import discord
import inspect

_help_attr = '__commands_help__'

def preserve_help(func):
	setattr(func, _help_attr, getattr(func, '__doc__'))
	return func

def injure_help(text):
	def decorator(cmd):
		set_help(cmd, text)
		return cmd

	return decorator

def get_help(cmd):
	return getattr(cmd.callback, _help_attr)

def set_help(cmd, text):
	setattr(cmd.callback, _help_attr, text)