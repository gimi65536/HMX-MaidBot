import inspect
import re
from typing import Optional

_help_attr = '__commands_help__'

def cleandoc(text: Optional[str]):
	if text is not None:
		doc = inspect.cleandoc(text)
		return re.sub(r' +', ' ', doc)
	return ''

def injure_help(text: Optional[str], locale = None):
	def decorator(cmd):
		set_help(cmd, text, locale)
		return cmd

	return decorator

def get_help(cmd) -> dict[Optional[str], str]:
	if hasattr(cmd, _help_attr):
		return getattr(cmd, _help_attr)

	doc: dict[Optional[str], str]
	if hasattr(cmd, 'callback'):
		doc = {None: cleandoc(cmd.callback.__doc__)}
	else:
		doc = {None: cleandoc(cmd.__doc__)}
	setattr(cmd, _help_attr, doc)
	return doc

def set_help(cmd, text: Optional[str], locale: Optional[str] = None):
	if hasattr(cmd, _help_attr):
		getattr(cmd, _help_attr)[locale] = cleandoc(text)
	else:
		setattr(cmd, _help_attr, {locale: cleandoc(text)})

def update_help(cmd, localization: dict[str, str]):
	if hasattr(cmd, _help_attr):
		getattr(cmd, _help_attr).update(localization)
	else:
		setattr(cmd, _help_attr, localization)