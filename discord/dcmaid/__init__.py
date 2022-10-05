from sys import version_info

if version_info < (3, 10):
	raise ImportError('Only for Python >= 3.10')