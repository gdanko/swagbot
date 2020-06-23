#!/usr/bin/env python3

from base64 import b64encode, b64decode
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from pprint import pprint
import logging
import os
import re
import sqlite3
import sys
import time

def dict_factory(cursor, row):
	d = {}
	for idx,col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d

def configure_logger():
	logger = logging.getLogger()
	handler = logging.StreamHandler()
	formatter = logging.Formatter("%(levelname)s %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)
	logger.propagate = False
	return logger

def get_input(text=None, default=None):
	if default:
		if (default.lower() == "yes"):
			prompt = "(Y/n)"
		elif (default.lower() == "no"):
			prompt = "(y/N)"
	else:
		prompt = None

	if prompt:
		message = "{} {} ".format(text, prompt)
		result = input(message)
		if (result == ""):
			result = default
		elif (result.lower() == "yes") or (result.lower() == "y"):
			result = "yes"
		else:
			result = "no"
	else:
		message = "{}".format(text)
		result = input(message)

	return result

def rsa_encrypt(message):	
	message = message.encode("utf-8")
	key = RSA.importKey(open(pubkey).read())
	cipher = PKCS1_OAEP.new(key)
	ciphertext = cipher.encrypt(message)
	return b64encode(ciphertext).decode("utf-8")

def is_file(path):
	try:
		if os.path.isfile(path):
			return True
		else:
			return False
	except:
		return False
	return False

def make_confdir():
	logger.info("Creating the bot configuration directory.")
	try:
		os.mkdir(confdir)
	except OSError as e:
		if e.errno == 17:
			pass
		else:
			logger.fatal("Failed: {}.".format(e))
			sys.exit(1)

def create_schema():
	logger.info("Creating the database schema.")
	config = {
		"tables": {
			"afk": {
				"columns": {
					"username": { "type": "text", "null": False, "primary_key": False },
					"message": { "type": "text", "null": False, "primary_key": False },
					"timestamp": { "type": "integer", "null": False, "primary_key": False }
				}
			},
			"autogreet": {
				"columns": {
					"id": { "type": "integer", "null": False, "primary_key": True, "unique": True },
					"username": { "type": "text", "null": False, "primary_key": False },
					"mention": { "type": "text", "null": False, "primary_key": False }
				}
			},
			"autoop": {
				"columns": {
					"username": { "type": "text", "null": False, "primary_key": False },
					"addedby": { "type": "text", "null": False, "primary_key": False }
				}
			},
			"command_settings": {
				"columns": {
					"command": { "type": "text", "null": False, "primary_key": True },
					"module": { "type": "text", "null": False, "primary_key": False },
					"enabled": { "type": "integer", "null": False, "primary_key": False, "default": 1 },
					"hidden": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"channels": { "type": "integer", "null": True, "primary_key": False }
				}
			},
			"commands": {
				"columns": {
					"command": { "type": "text", "null": False, "primary_key": True },
					"usage": { "type": "text", "null": False, "primary_key": False },
					"level": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"can_be_disabled": { "type": "integer", "null": False, "primary_key": False, "default": 1 },
					"module": { "type": "text", "null": False, "primary_key": False },
					"method": { "type": "text", "null": False, "primary_key": False },
					"type": { "type": "text", "null": False, "primary_key": False },
					"monospace": { "type": "integer", "null": False, "primary_key": False, "default": 0 }
				}
			},
			"curses": {
				"columns": {
					"username": { "type": "text", "null": False, "primary_key": False },
					"curses_count": { "type": "integer", "null": False, "primary_key": False },
					"last_curse_time": { "type": "integer", "null": False, "primary_key": False },
					"last_curse_word": { "type": "text", "null": False, "primary_key": False },
					"last_curse_channel": { "type": "text", "null": False, "primary_key": False }
				}
			},
			"curse_words": {
				"columns": {
					"word": { "type": "text", "null": False, "unique": True }
				}
			},
			"links": {
				"columns": {
					"title": { "type": "text", "null": False, "primary_key": False },
					"url": { "type": "text", "null": False, "primary_key": False },
					"addedby": { "type": "text", "null": False, "primary_key": False }
				}
			},
			"modules": {
				"columns": {
					"module": { "type": "text", "null": False, "primary_key": False },
					"enabled": { "type": "integer", "null": False, "primary_key": False, "default": 1 },
					"can_be_disabled": { "type": "integer", "null": False, "primary_key": False, "default": 0 }
				},
			},
			"greetings": {
				"columns": {
					"language": { "type": "text", "null": False, "unique": True, "primary_key": True },
					"greeting": { "type": "text", "null": False, "unique": False, "primary_key": False },
				},
			},
			"quotes": {
				"columns": {
					"quote": { "type": "text", "null": False, "primary_key": False },
					"category": { "type": "text", "null": False, "primary_key": False }
				},
			},
			"seen": {
				"columns": {
					"username": { "type": "text", "null": False, "primary_key": False },
					"time": { "type": "integer", "null": False, "primary_key": False },
					"channel": { "type": "text", "null": False, "primary_key": False }
				},
			},
			"tickers": {
				"columns": {
					"name": { "type": "text", "null": False, "primary_key": False },		
					"interval": { "type": "integer", "null": False, "primary_key": False },
					"targets": { "type": "text", "null": False, "primary_key": False },
					"enabled": { "type": "integer", "null": False, "primary_key": False, "default": 1 }
				},
			},
			"timers": {
				"columns": {
					"title": { "type": "text", "null": False, "unique": True, "primary_key": False },
					"description": { "type": "text", "null": False, "primary_key": False },
					"expires": { "type": "integer", "null": False, "primary_key": False },
					"expired": { "type": "integer", "null": False, "primary_key": False }
				}
			},
			"users": {
				"columns": {
					"username": { "type": "text", "null": False, "primary_key": True },
					"password": { "type": "text", "null": False, "primary_key": False },
					"level": { "type": "integer", "null": False, "primary_key": False },
					"last_auth": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"failed_logins": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"last_failed_login": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"locked": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"must_change_pw": { "type": "integer", "null": False, "primary_key": False, "default": 1 }
				}
			},
			"bot_users": {
				"columns": {
					"id": { "type": "text", "null": False, "unique": True, "primary_key": True },
					"username": { "type": "text", "null": False, "unique": True, "primary_key": False },
					"password": { "type": "text", "null": False, "primary_key": False },
					"level": { "type": "integer", "null": False, "default": 0 },
					"last_auth": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"failed_logins": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"last_failed_login": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"locked": { "type": "integer", "null": False, "primary_key": False, "default": 0 },
					"must_change_pw": { "type": "integer", "null": False, "primary_key": False, "default": 1 }
				}
			},
			"slack_account_cache": {
				"columns": {
					"id": { "type": "text", "null": False, "unique": True, "primary_key": True },
					"username": { "type": "text", "null": False, "unique": True, "primary_key": False },
					"deleted": { "type": "integer", "null": False, "unique": False, "primary_key": False, "default": 0 },
					"is_bot": { "type": "integer", "null": False, "unique": False, "primary_key": False, "default": 0 },
					"is_app_user": { "type": "integer", "null": False, "unique": False, "primary_key": False, "default": 0 },
					"real_name": { "type": "text", "null": False, "unique": False, "primary_key": False },
					"updated": { "type": "integer", "null": False, "unique": False, "primary_key": False }
				}
			},
			"currency_conversion": {
				"columns": {
					"nation": { "type": "text", "null": False, "primary_key": False },
					"symbol": { "type": "text", "null": False, "primary_key": False }
				}
			}
		}	
	}

	for table_name, table_obj in config["tables"].items():
		drop = "DROP TABLE IF EXISTS {}".format(table_name)
		res = cursor.execute(drop)
		conn.commit()

		create_arr = []
		for col_name, col_obj in table_obj["columns"].items():
			arr = []
			arr.append("{} {}".format(col_name, col_obj["type"].upper()))
			if "null" in col_obj and col_obj["null"] == False:
				arr.append("NOT NULL")
			if "primary_key" in col_obj and col_obj["primary_key"] == True:
				arr.append("PRIMARY KEY")
			if "unique" in col_obj and col_obj["unique"] == True:
				arr.append("UNIQUE")
			if "default" in col_obj:
				arr.append("DEFAULT {}".format(col_obj["default"]))
			create_arr.append(" ".join(arr))
		create = "CREATE TABLE {} ({})".format(table_name, ", ".join(create_arr))
		cursor.execute(create)
		conn.commit()

def enable_core_plugin():
	logger.info("Enabling the plugin swagbot.plugins.core.")
	try:
		insert = "INSERT INTO modules (module,enabled,can_be_disabled) VALUES('swagbot.plugins.core',1,0)"
		cursor.execute(insert)
		conn.commit()
	except sqlite3.IntegrityError as e:
		logger.fatal("Failed to enable the core plugin: {}".format(e))
		sys.exit(1)

def populate_greetings_table():
	file = "./greetings.txt"
	if is_file(file):
		logger.info("Populating the greeting table.")
		cursor.execute("DELETE FROM greetings")
		with open(file) as lines:
			for line in lines:
				line = line.rstrip()
				language,greeting = re.split("\s*,\s*", line)
				insert = "INSERT INTO greetings (language,greeting) VALUES(?,?)"
				cursor.execute(insert, (
					language,
					greeting
				))
				conn.commit()
	else:
		logger.warn("Could not populate the currency symbols table because {} not found.".format(file))

def create_admin_user():
	logger.info("Creating the admin user.")
	insert = "INSERT INTO bot_users (id,username,password,level,must_change_pw) VALUES (?,?,?,?,?)"
	cursor.execute(insert, (
		admin_id,
		admin_username,
		rsa_encrypt(admin_password),
		99,
		0
	))
	conn.commit()

logger = configure_logger()
admin_id = None
admin_username = None
admin_password = None
confdir = "{}/.swagbot".format(os.path.expanduser("~"))
pubkey = "{}/bot-public.pem".format(confdir)
database = "{}/bot.db".format(confdir)
conn = sqlite3.connect(database, check_same_thread=False)
conn.row_factory = dict_factory
cursor = conn.cursor()

result = get_input(
	text="This will completely destroy any existing swagbot database in '{}'. Are you sure you want to do this?".format(confdir),
	default="no"
)
if result == "yes":
	admin_id = get_input("Please enter the admin user's Slack ID: ")
	admin_username = get_input("Please enter the admin user's username: ")
	admin_password = get_input("Please enter the admin user's password: ")
	make_confdir()
	create_schema()
	enable_core_plugin()
	populate_greetings_table()
	create_admin_user()
	logger.info("The database setup is complete.")
else:
	print("Aborting.")
