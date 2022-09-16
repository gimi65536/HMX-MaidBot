import discord
import inspect
import re

_help_attr = '__commands_help__'

def cleandoc(text):
	if text is not None:
		doc = inspect.cleandoc(text)
		return re.sub(r' +', ' ', doc)
	return None

def injure_help(text):
	def decorator(cmd):
		set_help(cmd, text)
		return cmd

	return decorator

def get_help(cmd):
	if hasattr(cmd, _help_attr):
		return getattr(cmd, _help_attr)

	doc = cleandoc(cmd.callback.__doc__)
	setattr(cmd, _help_attr, doc)
	return doc

def set_help(cmd, text):
	setattr(cmd, _help_attr, cleandoc(text))