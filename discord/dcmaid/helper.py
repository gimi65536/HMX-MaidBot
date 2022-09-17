import discord
import inspect
import re
from typing import Dict, Optional

_help_attr = '__commands_help__'

def cleandoc(text):
	if text is not None:
		doc = inspect.cleandoc(text)
		return re.sub(r' +', ' ', doc)
	return None

def injure_help(text, locale = None):
	def decorator(cmd):
		set_help(cmd, text, locale)
		return cmd

	return decorator

def get_help(cmd) -> Dict[Optional[str], str]:
	if hasattr(cmd, _help_attr):
		return getattr(cmd, _help_attr)

	doc = {None: cleandoc(cmd.callback.__doc__)}
	setattr(cmd, _help_attr, doc)
	return doc

def set_help(cmd, text, locale = None):
	if hasattr(cmd, _help_attr):
		getattr(cmd, _help_attr)[locale] = cleandoc(text)
	else:
		setattr(cmd, _help_attr, {locale: cleandoc(text)})

def update_help(cmd, localization: Dict[str, str]):
	if hasattr(cmd, _help_attr):
		getattr(cmd, _help_attr).update(localization)
	else:
		setattr(cmd, _help_attr, localization)