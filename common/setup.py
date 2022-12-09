from distutils.core import setup

setup(
	name = 'common',
	version = '0.4',
	description = 'Common utilities used in HMX-MaidBot project',
	packages = ['rollgames', 'simple_parsers'],
	py_modules = ['proxy_types', 'reader'],
	install_requires = [
		'more_itertools>=9',
		'pyparsing>=3.0.9',
	]
)
