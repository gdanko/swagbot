import os
from setuptools import setup, find_packages

def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name = "swagbot",
	version = "0.1.4",
	author = "Gary Danko",
	author_email = "gdanko@gmail.com",
	url = "https://github.intuit.com/gdanko/swagbot",
	license = "GPLv3",
	description = "A powerful and flexible Slack bot",
	packages = ["swagbot", "swagbot.plugins"],
	package_dir = {
		"swagbot": "swagbot",
		"swagbot.plugins": "swagbot/plugins"
	},
	install_requires = ["requests", "PyCryptodome"],

	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers = [
		"Development Status :: 4 - Beta",
		"Environment :: Console",
		"Intended Audience :: System Administrators",
		"License :: Other/Proprietary License",
		"Operating System :: POSIX :: Other",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.3",
		"Programming Language :: Python :: 3.4",
		"Programming Language :: Python :: 3.5"
	]
)
