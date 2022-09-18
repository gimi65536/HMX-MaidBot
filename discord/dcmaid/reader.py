import json
from pathlib import PurePath
from typing import TextIO, Tuple
from .utils import add_suffix

class BaseReader:
	support_suffices: Tuple[str, ...] = ()

	@classmethod
	def load(cls, path: PurePath):
		obj = None
		for suffix in cls.support_suffices:
			try:
				with open(add_suffix(path, suffix)) as f:
					obj = cls.process(f)
			except:
				continue
			else:
				return obj
		return None

	@classmethod
	def process(cls, f: TextIO):
		raise NotImplementedError

class JSONReader(BaseReader):
	support_suffices = ('.json', '.js')

	@classmethod
	def process(cls, f: TextIO):
		return json.load(f)

class JSON5Reader(BaseReader):
	support_suffices = ('.json5', )

	@classmethod
	def process(cls, f: TextIO):
		import pyjson5
		return pyjson5.load(f)

class YAMLReader(BaseReader):
	support_suffices = ('.yaml', '.yml')

	@classmethod
	def process(cls, f: TextIO):
		import yaml
		return yaml.load(f)

class TOMLReader(BaseReader):
	support_suffices = ('.yaml', '.yml')

	@classmethod
	def process(cls, f: TextIO):
		import tomllib
		return tomllib.load(f)

# This class is here for future implemetation...
class CUEReader(BaseReader):
	pass

_readers = (JSONReader, YAMLReader, JSON5Reader, TOMLReader)

def load(filename):
	path = PurePath(filename)
	for reader in _readers:
		obj = reader.load(path)
		if obj is not None:
			return obj

	return None

__all__ = (
	'BaseReader',
	'JSONReader',
	'YAMLReader',
	'JSON5Reader',
	'TOMLReader',
	'load'
)
