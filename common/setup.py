from distutils.core import setup

setup(
	name = 'common',
	version = '0.4',
	description = 'Common utilities used in HMX-MaidBot project',
	packages = ['proxy_types', 'reader', 'rollgames', 'simple_parsers'],
	package_data = {
		'proxy_types': ['py.typed'],
		'reader': ['py.typed'],
		'rollgames': ['games.*', 'py.typed'],
		'simple_parsers': ['py.typed']
	},
	install_requires = [
		'more_itertools>=9',
		'pyparsing>=3.0.9',
	]
)
