import os
import sqlite3
import re
import sys
import time
from pprint import pprint

# Create exceptions
def update_plugin_commands(module=None, methods=None):
	for command_name, command_settings in methods.items():
		method = command_settings["method"] if "method" in command_settings else command_name
		monospace = command_settings["monospace"] if "monospace" in command_settings else 0
		hidden = command_settings["hidden"] if "hidden" in command_settings else 0

		select = "SELECT * FROM commands WHERE command='{}'".format(command_name)
		cursor.execute(select)
		count = len(cursor.fetchall())

		if count <= 0:
			insert = "INSERT OR REPLACE INTO commands (command,usage,level,can_be_disabled,module,method,type,monospace) VALUES (?,?,?,?,?,?,?,?)"
			cursor.execute(insert, (
				command_name,
				command_settings["usage"],
				command_settings["level"],
				command_settings["can_be_disabled"],
				module,
				method,
				command_settings["type"],
				monospace
			))
			conn.commit()
		else:
			update = "UPDATE commands SET usage=?,level=?,can_be_disabled=?,module=?,method=?,type=?,monospace=? WHERE command='{}'".format(command_name)
			cursor.execute(update, (
				command_settings["usage"],
				command_settings["level"],
				command_settings["can_be_disabled"],
				module,
				method,
				command_settings["type"],
				monospace
			))
			conn.commit()

		select = "SELECT * FROM command_settings WHERE command='{}'".format(command_name)
		cursor.execute(select)
		count = len(cursor.fetchall())

		if count <= 0:
			insert = "INSERT OR REPLACE INTO command_settings (command,module,enabled,hidden) VALUES (?,?,?,?)"
			cursor.execute(insert, (
				command_name,
				module,
				1,
				hidden
			))
			conn.commit()

def populate_account_cache(userlist=None):
	now = int(time.time())
	for member in userlist["members"]:
		real_name = None
		if "real_name" in member:
			real_name = member["real_name"]
		elif "real_name" in member["profile"]:
			real_name = member["profile"]["real_name"]
		elif "real_name_normalized" in member["profile"]:
			real_name = member["profile"]["real_name_normalized"]
		elif "first_name" in member["profile"] and "last_name" in member["profile"]:
			real_name = "{} {}".format(member["profile"]["first_name"], member["profile"]["last_name"])
		else:
			real_name = "unknown"

		insert = "INSERT OR REPLACE INTO slack_account_cache (id,username,deleted,is_bot,is_app_user,real_name,updated) VALUES (?,?,?,?,?,?,?)"
		cursor.execute(insert, (
			member["id"],
			member["name"],
			1 if member["deleted"] == True else 0,
			1 if member["is_bot"] == True else 0,
			1 if member["is_app_user"] == True else 0,
			real_name,
			now,
		))
		conn.commit()

# Help and usage functions
def help():
	commands = []
	select = "SELECT commands.*, command_settings.* FROM commands JOIN command_settings ON commands.command=command_settings.command AND command_settings.enabled=1 AND command_settings.hidden=0 ORDER BY command"
	res = cursor.execute(select)
	conn.commit()
	for row in res:
		commands.append(row["command"])
	return commands

def usage(command=None):
	select = "SELECT usage FROM commands WHERE command='{}'".format(command)
	cursor.execute(select)
	result = cursor.fetchone()
	return result["usage"] if result else None

# User functions
def get_user_from_cache(id=None, username=None):
	if id:
		selector = "id"
		selected = id
	elif username:
		# Change this
		selector = "username"
		selected = username
	select = "SELECT * FROM slack_account_cache WHERE {}='{}' AND deleted=0 AND is_bot=0 AND is_app_user=0".format(selector, selected)
	cursor.execute(select)
	result = cursor.fetchone()
	return result if result else None

def get_user(id=None, username=None):
	if id:
		selector = "id"
		selected = id
	elif username:
		selector = "username"
		selected = username
	select = "SELECT * FROM bot_users WHERE {}='{}'".format(selector, selected)
	cursor.execute(select)
	result = cursor.fetchone()
	if result:
		result["locked"] = True if ("locked" in result and result["locked"] == 1) else False
		result["must_change_pw"] = True if ("must_change_pw" in result and result["must_change_pw"] == 1) else False
		return result
	else:
		return None

def useradd(id=None, username=None, password=None, level=None):
	insert = "INSERT INTO bot_users (id,username,password,level) VALUES (?,?,?,?)"
	cursor.execute(insert, (
		id,
		username,
		password,
		level
	))
	conn.commit()

def userdel(username=None):
	delete = "DELETE FROM bot_users WHERE username='{}'".format(username)
	cursor.execute(delete)
	conn.commit()

def userreset(username=None):
	update = "UPDATE bot_users SET last_auth=0,failed_logins=0,last_failed_login=0,locked=0,must_change_pw=1 WHERE username='{}'".format(username)
	cursor.execute(update)
	conn.commit()

def users():
	rows = []
	select = "SELECT * FROM bot_users"
	res = cursor.execute(select)
	conn.commit()
	for row in res:
		rows.append(row)
	return rows	

# Authentication functions
def reset_failed_logins(username=None):
	update = "UPDATE bot_users SET failed_logins=0,locked=0 WHERE username='{}'".format(username)
	cursor.execute(update)

def user_auth_successful(username=None):
	update = "UPDATE bot_users SET last_auth={},failed_logins=0,last_failed_login=0,locked=0 WHERE username='{}'".format(now(), username)
	cursor.execute(update)
	conn.commit()

def increment_last_failed(username=None, now=None):
	user = get_user(username=username)
	if user:
		failed_logins = user["failed_logins"] + 1
		update = "UPDATE bot_users SET last_failed_login={},failed_logins={} WHERE username='{}'".format(now, failed_logins, username)
		cursor.execute(update)
		conn.commit()

def update_last_failed_login_time(username=None, now=None):
	user = get_user(username=username)
	if user:
		update = "UPDATE bot_users SET last_failed_login={} WHERE username='{}'".format(now, username)
		cursor.execute(update)
		conn.commit()

def lock_account(username=None, now=None):
	user = get_user(username=username)
	if user:
		failed_logins = user["failed_logins"] + 1
		update = "UPDATE bot_users SET last_failed_login={},failed_logins={},locked=1 WHERE username='{}'".format(now, failed_logins, username)
		cursor.execute(update)
		conn.commit()

def deauth_user(username=None, now=None):
	update = "UPDATE bot_users SET last_auth=0 WHERE username='{}'".format(username)
	cursor.execute(update)
	conn.commit()

def update_password(username=None, password=None):
	update = "UPDATE bot_users SET password='{}' WHERE username='{}'".format(password, username)
	cursor.execute(update)
	conn.commit()

# Command functions
def all_commands():
	commands = []
	select = "SELECT command FROM commands"
	res = cursor.execute(select)
	conn.commit()
	for row in res:
		commands.append(row["command"])
	return commands	

def command_lookup(command=None):
	select = "SELECT commands.command, commands.usage, commands.level, commands.can_be_disabled, commands.module, commands.method, commands.type, commands.monospace, command_settings.enabled, command_settings.hidden FROM commands JOIN command_settings ON commands.command = command_settings.command WHERE commands.command='{}'".format(command)
	cursor.execute(select)
	result = cursor.fetchone()
	if result:
		result["can_be_disabled"] = True if ("can_be_disabled" in result and result["can_be_disabled"] == 1) else False
		result["enabled"] = True if ("enabled" in result and result["enabled"] == 1) else False
		result["hidden"] = True if ("hidden" in result and result["hidden"] == 1) else False
		result["monospace"] = True if ("monospace" in result and result["monospace"] == 1) else False
		return result
	else:
		return None

def prune_commands_table(commands=None):
	delete = "DELETE FROM commands WHERE command IN ({})".format(quote_list(commands))
	cursor.execute(delete)
	conn.commit()

def disable_command(command=None):
	update = "UPDATE command_settings SET enabled=0 WHERE command='{}'".format(command)
	cursor.execute(update)
	conn.commit()

def enable_command(command=None):
	update = "UPDATE command_settings SET enabled=1 WHERE command='{}'".format(command)
	cursor.execute(update)
	conn.commit()

def unhide_command(command=None):
	update = "UPDATE command_settings SET hidden=0 WHERE command='{}'".format(command)
	cursor.execute(update)
	conn.commit()

def hide_command(command=None):
	update = "UPDATE command_settings SET hidden=1 WHERE command='{}'".format(command)
	cursor.execute(update)
	conn.commit()

# Module functions
def get_module(module=None):
	select = "SELECT * FROM modules WHERE module='{}'".format(module)
	cursor.execute(select)
	result = cursor.fetchone()
	return result if result else False

def moduleadd(module=None):
	insert = "INSERT INTO modules (module,enabled,can_be_disabled) VALUES (?,?,?)"
	cursor.execute(insert, (
		module,
		0,
		1
	))
	conn.commit()

def module_commands(module=None):
	commands = []
	select = "SELECT command FROM commands WHERE module='{}'".format(module)
	print(select)
	res = cursor.execute(select)
	for row in res:
		commands.append(row["command"])
	return commands

def disablemod(module=None):
	delete = "DELETE FROM commands WHERE module='{}'".format(module)
	cursor.execute(delete)
	conn.commit()

	update = "UPDATE modules SET enabled=0 WHERE module='{}'".format(module)
	cursor.execute(update)
	conn.commit()

def enablemod(module=None):
	update = "UPDATE modules SET enabled=1 WHERE module='{}'".format(module)
	cursor.execute(update)
	conn.commit()

# Other functions
def _dict_factory(cursor, row):
	d = {}
	for idx,col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d

def quote_list(l):
	return ",".join(["\'{}\'".format(x) for x in l])

def now():
	return int(time.time())

dbfile = "{}/.swagbot/bot.db".format(os.path.expanduser("~"))
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = _dict_factory
cursor = conn.cursor()
