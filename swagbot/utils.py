from distutils.version import LooseVersion, StrictVersion
from pprint import pprint
import datetime
import inspect
import json
import logging
import os
import platform
import random
import re
import swagbot.database as db
import swagbot.exception as exception
import sys
import time
import yaml

# Set up the logger
def configure_logger(loggerid=None, debug=False):
	if loggers.get(loggerid):
		return loggers.get(loggerid)
	else:
		level = logging.DEBUG if debug == True else logging.INFO

		logger = logging.getLogger(loggerid)
		handler = logging.StreamHandler()
		formatter = logging.Formatter("%(asctime)s.%(msecs)06d [%(levelname)s] %(message)s", "%s")
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		logger.setLevel(level)
		logger.propagate = False
		loggers[loggerid] = logger
	return logger

# Config file functions
def read_config(config_file=None):
	try:
		contents = open(config_path, "r").read()
		return contents
	except OSError as e:
		if e.errno == 2:
			raise exception.ConfigFileRead(path=config_file, message="No such file or directory")
		elif e.errno == 13:
			raise exception.ConfigFileRead(path=config_file, message="Permission denied")
		elif e.errno == 21:
			raise exception.ConfigFileRead(path=config_file, message="Is a directory")
		else:
			raise exception.ConfigFileRead(path=config_file, message=str(s))

def parse_config(config_file=None):
	contents = open(config_file, "r").read()

	if len(contents) <= 0:
		raise exception.InvalidConfigFile(path=config_path, message="Zero-length file")

	config = validate_yaml(contents)
	if config:
		return config

# Validators
def validate_url(string):
	regex = "^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
	if re.match(regex, string):
		return True
	return False

def validate_yaml(string):
	hash = yaml.load(string)
	if string:
		try:
			hash = yaml.load(string)
			return hash
		except:
			return None
	else:
		return None

def validate_json(string):
	if string:
		try:
			hash = json.loads(string)
			return hash
		except:
			return None
	else:
		return None

# Miscellaneous functions
def now():
	return int(time.time())

def classname(c):
	try:
		module = c.__class__.__module__
		name = c.__class__.__name__
		return "{}.{}".format(module, name)
	except:
		print("need a 'not a class' exception")
		sys.exit(1)

def generate_random(length=8):
	return "".join(random.choice("0123456789abcdef") for x in range(length))

def duration(seconds):
	seconds = int(seconds)
	days = int(seconds / 86400)
	hours = int(((seconds - (days * 86400)) / 3600))
	minutes = int(((seconds - days * 86400 - hours * 3600) / 60))
	secs = int((seconds - (days * 86400) - (hours * 3600) - (minutes * 60)))
	output = []
	if days > 0:
		output.append("{}d".format(days))
	if hours > 0:
		output.append("{}h".format(hours))
	if minutes > 0:
		output.append("{}m".format(minutes))
	if secs > 0:
		output.append("{}s".format(secs))
	return " ".join(output)

def farenheit_to_celsius(temp):
	temp = int(temp)
	c = (((temp - 32) * 5) / 9)
	return int(c)

def celsius_to_farenheit(temp):
	temp = int(temp)
	c = (((temp * 9) / 5) + 32)
	return int(c)

def make_success(client, content_key=None, content=None):
	make_response(client, success=True, content_key=content_key, content=content)

def make_error(client, recipient=None, content_key=None, content=None):
	make_response(client, success=False, content_key=content_key, content=content)

def make_response(client, success=None, content_key=None, content=None):
	client.success = success
	status = "success" if success == True else "error"

	if content_key:	
		response = {"status": status, content_key: content}
	else:
		if content:
			if isinstance(content, dict):
				response = content
				response["status"] = status
			elif isinstance(content, list):
				response = {"status": status, "messages": content}
			elif isinstance(content, str):
				response = {"status": status, "messages": [content]}
		else:
			response = {"status": status, "messages": "Unknown"}
	client.response = response

def __check_python_version(req_version):
	cur_version = sys.version_info
	if cur_version <= req_version:
		logger.fatal("Your Python interpreter is too old. Please upgrade to {}.{} or greater.".format(req_version[0], req_version[1]))
		sys.exit(1)

def check_environment():
	__check_python_version((3, 0))

version = sys.version_info
major = version[0]
loggers = {}
logger = configure_logger(loggerid="logger-{}".format(generate_random(length=32)), debug=False)
