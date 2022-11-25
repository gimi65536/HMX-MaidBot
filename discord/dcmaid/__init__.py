from sys import version_info

if version_info < (3, 11):
	raise ImportError('Only for Python >= 3.11')