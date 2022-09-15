import discord
import inspect

_help_attr = '__commands_help__'

def injure_help(text):
	def decorator(cmd):
		set_help(cmd, text)
		return cmd

	return decorator

def get_help(cmd):
	if hasattr(cmd, _help_attr):
		return getattr(cmd, _help_attr)

	doc = cmd.callback.__doc__
	if doc is not None:
		doc = inspect.cleandoc(doc)
	setattr(cmd, _help_attr, doc)
	return doc

def set_help(cmd, text):
	setattr(cmd, _help_attr, inspect.cleandoc(text))