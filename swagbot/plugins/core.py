from base64 import b64encode, b64decode
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from datetime import datetime
from pprint import pprint, pformat
from swagbot.core import BasePlugin
import argparse
import calendar
import geopy
import os
import random
import re
import swagbot.database as db
import swagbot.request as request
import swagbot.utils as utils
import sys
import time

class Plugin(BasePlugin):
	def __init__(self, bot):
		self.classname = self.__class__.__module__.split(".")[-1]
		self.methods = self.__setup_methods()
		BasePlugin.__init__(self, bot)

		self.default_user_passwd = self.bot.config["default_user_passwd"]
		self.session_timeout = self.bot.config["session_timeout"]
		self.googleapis_key = self.bot.config["keys"]["googleapis"]

	def auth(self, command=None):
		if command:
			if command.user:
				if command.command_args:
					password = command.command_args
					now = utils.now()
					max_attempts = 3

					failed_logins = int(command.user["failed_logins"])
					last_failed = int(command.user["last_failed_login"])
					account_locked = command.user["locked"]
					increment_failed_logins = failed_logins + 1

					# If locked and last bad login > 10 min, unlock the user
					if ((now - last_failed) > 600):
						db.reset_failed_logins(username=command.user["username"])
						account_locked = False
						failed_logins = 0

					if account_locked == True:
						utils.make_error(command, content="Account locked.")
						return

					# Account is not locked, validate password
					if password == self.__rsa_decrypt(command.user["password"]):
						db.user_auth_successful(username=command.user["username"])
						utils.make_success(command, content="Login successful. Your session will expire in {} minutes.".format(int(self.session_timeout / 60)))
						return

					else:
						db.update_last_failed_login_time(username=command.user["username"], now=now)
						last_failed = now

						if (increment_failed_logins < max_attempts) and ((now - last_failed) < 600):
							db.increment_last_failed(username=command.user["username"], now=now)
							utils.make_error(command, content="Login failed.")
							return

						elif increment_failed_logins >= max_attempts:
							db.lock_account(username=command.user["username"], now=now)
							utils.make_error(command, content="Login failed. Your account has been locked due to excessive login failures. Please contact a bot administrator.")
							return

				else:
					utils.make_error(command, content=["No password specified.", "Usage: {}".format(command.command["usage"])])
					return
			else:
				utils.make_error(command, content="You're not registered with me.")
				return

		else:
			utils.make_error(command, content="An unknown error has occurred.")
			return

	def deauth(self, command=None):
		if command:
			if command.user:
				db.deauth_user(username=command.user["username"])
				utils.make_success(command, content="Session data removed.")
			else:
				utils.make_error(command, content="You're not registered with me.")
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def disable(self, command=None):
		if command:
			if command.command_args:
				command_name = command.command_args
				to_disable = db.command_lookup(command=command_name)
				if to_disable:
					if to_disable["enabled"] == True:
						if to_disable["can_be_disabled"] == True:
							db.disable_command(command=command_name)
							utils.make_success(command, content="The command \"{}\" was disabled.".format(command_name))
						else:
							utils.make_error(command, content="The command \"{}\" cannot be disabled.".format(command_name))
					else:
						utils.make_error(command, content="The command \"{}\" is already disabled.".format(command_name))
				else:
					utils.make_error(command, content="The command \"{}\" was not found.".format(command_name))
			else:
				utils.make_error(command, content=["No command specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")


	def disablemod(self, command=None):
		if command:
			module_name = command.command_args
			if module_name:				
				module_obj = db.get_module(module=module_name)
				if module_obj:
					if module_obj["enabled"] == 1:
						if module_obj["can_be_disabled"] == 1:
							commands = db.module_commands(module=module_name)
							db.disablemod(module=module_name)
							self.bot.load_plugins()
							messages = ["Disabled module {}.".format(module_name)]

							if len(commands) > 0:
								messages.append("The following commands will no longer be available: {}.".format(", ".join(sorted(commands))))
							utils.make_success(command, content=" ".join(messages))
						else:
							utils.make_error(command, content="Module {} cannot be disabled.".format(module_name))
					else:
						utils.make_error(command, content="Module {} is already disabled. Nothing to do.".format(module_name))
				else:
					utils.make_error(command, content="Module {} not found in the modules table.".format(module_name))
			else:
				utils.make_error(command, content=["No module specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def enable(self, command=None):
		if command:
			if command.command_args:
				command_name = command.command_args
				to_enable = db.command_lookup(command=command_name)
				if to_enable:
					if to_enable["enabled"] == False:
						db.enable_command(command=command_name)
						utils.make_success(command, content="The command \"{}\" was enabled.".format(command_name))
					else:
						utils.make_error(command, content="The command \"{}\" is already enabled.".format(command_name))
				else:
					utils.make_error(command, content="The command \"{}\" was not found.".format(command_name))
			else:
				utils.make_error(command, content=["No command specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def enablemod(self, command=None):
		if command:
			module_name = command.command_args
			if module_name:
				module_obj = db.get_module(module=module_name)
				if module_obj:
					if module_obj["enabled"] == 0:
						db.enablemod(module=module_name)
						self.bot.load_plugins()
						messages = ["Enabled module {}.".format(module_name)]
						commands = db.module_commands(module=module_name)
						# FIX THIS
						if len(commands) > 0:
							messages.append("The following commands are now available: {}.".format(", ".join(sorted(commands))))
						utils.make_success(command, content=" ".join(messages))
					else:
						utils.make_error(command, content="Module {} is already enabled. Nothing to do.".format(module_name))
				else:
					utils.make_error(command, content="Module {} not found in the modules table.".format(module_name))
			else:
				utils.make_error(command, content=["No module specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def greeting(self, command=None):
		if command:
			language = command.command_args
			greeting = db.greeting(language=language)
			if greeting:
				utils.make_success(command, content="{}! This is how you greet someone in {}.".format(greeting["greeting"], greeting["language"]))
			else:
				if language:
					utils.make_error(command, content="Sorry! I do not know how to greet someone in {}.".format(language))
				else:
					utils.make_error(command, content="Oops! I was not able to find any available greetings.")
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def help(self, command=None):
		if command:
			if command.command_args:
				help_command = command.command_args
				usage = db.usage(command=help_command)
				if usage:
					utils.make_success(command, content=usage)
				else:
					utils.make_error(command, content="No usage information found for {}".format(help_command))
			else:
				commands = db.help()
				if commands:
					messages = []
					messages.append("Available command are:")
					messages.append(", ".join(commands))
					messages.append("Use help <command> for command usage.")
					utils.make_success(command, content=messages)
				else:
					utils.make_error(command, content="An error occurred while fetching the help.")
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def hide(self, command=None):
		if command:
			command_name = command.command_args
			if command_name:
				to_hide = db.command_lookup(command=command_name)
				if to_hide:
					if to_hide["hidden"] == False:
						db.hide_command(command=command_name)
						utils.make_success(command, content="The command \"{}\" was hidden.".format(command_name))
					else:
						utils.make_error(command, content="The command \"{}\" is already hidden.".format(command_name))
				else:
					utils.make_error(command, content="The command \"{}\" was not found.".format(command_name))
			else:
				utils.make_error(command, content=["No command specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def passwd(self, command=None):
		if command:
			opts = command.command_args
			if opts:
				old_passwd, new_passwd = re.split("\s+", opts)
				if old_passwd and new_passwd:
					if command.user:
						if old_passwd == self.__rsa_decrypt(command.user["password"]):
							if old_passwd == new_passwd:
								utils.make_error(command, content="Old password and new password cannot be the same.")
							elif new_passwd == self.default_user_passwd:
								utils.make_error(command, content="You cannot use that password.")
							elif new_passwd:
								encrypted = self.__rsa_encrypt(new_passwd)
								db.update_password(username=command.user["username"], password=encrypted)
								utils.make_success(command, content="Password successfully changed.")
						else:
							utils.make_error(command, content="Incorrect old password.")
					else:
						utils.make_error(command, content="You do not appear to be registered as a user. If this is an error, please contact a bot administrator.")
				else:
					utils.make_error(command, content=["Invalid input.", "Usage: {}".format(command.command["usage"])])
			else:
				utils.make_error(command, content=["No passwords specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")
			
	def refresh_account_cache(self, command=None):
		utils.make_success(command, content="Refreshing the Slack account cache.")
		self.bot.populate_account_cache()

	def reload(self, command=None):
		messages = []
		messages.append("before:")
		for plugin_name, plugin in self.bot.plugins.items():
			messages.append(str(plugin))
		self.bot.load_plugins()
		messages.append("after:")
		for plugin_name, plugin in self.bot.plugins.items():
			messages.append(str(plugin))
		utils.make_success(command, content=messages)

	def time(self, command=None):
		now = utils.now()
		if command:
			location = command.command_args
			if location:
				uri = "https://maps.googleapis.com/maps/api/geocode/json?address={}&sensor=false&key={}".format(location, self.googleapis_key)
				request.get(self, uri=uri)
				if self.success:
					lat = self.response["results"][0]["geometry"]["location"]["lat"]
					lng = self.response["results"][0]["geometry"]["location"]["lng"]
					location = self.response["results"][0]["formatted_address"]
					uri = "https://maps.googleapis.com/maps/api/timezone/json?location={},{}&timestamp={}&sensor=false".format(lat, lng, now)
					request.get(self, uri=uri)
					if self.success:
						offset = self.response["rawOffset"]
						d = datetime.utcnow()
						utc_time = time.mktime(d.timetuple())
						local_time = utc_time + offset
						local_time_human = datetime.fromtimestamp(local_time).strftime("%H:%M:%S")
						utils.make_error(command, content="It is currently {} in {}.".format(local_time_human, location))
				else:
					utils.make_error(command, content="Failed to get the time in {}.".format(location))
			else:
				utils.make_success(command, content="It is now {}.".format(int(time.time())))
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def unhide(self, command=None):
		if command:
			command_name = command.command_args
			if command_name:
				to_unhide = db.command_lookup(command=command_name)
				if to_unhide:
					if to_unhide["hidden"] == True:
						db.unhide_command(command=command_name)
						utils.make_success(command, content="The command \"{}\" was unhidden.".format(command_name))
					else:
						utils.make_error(command, content="The command \"{}\" is already unhidden.".format(command_name))
				else:
					utils.make_error(command, content="The command \"{}\" was not found.".format(command_name))
			else:
				utils.make_error(command, content=["No command specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def uptime(self, command=None):
		if command:
			seconds = utils.now() - int(command.bot.ready_time)
			if seconds == 0: seconds = 1
			uptime = utils.duration(seconds)
			utils.make_success(command, content="uptime {}".format(uptime))
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def useradd(self, command=None):
		if command:
			sys.argv = command.argv
			parser = argparse.ArgumentParser(description=command.command["usage"])
			parser.add_argument("-u", "--username", help="The username.", required=True)
			parser.add_argument("-l", "--level", help="The level.", required=True)
			try:
				args = parser.parse_args()
			except:
				utils.make_error(command, content=["Invalid input received.", "Usage: {}".format(command.command["usage"])])
				return

			user = db.get_user_from_cache(username=args.username)
			if user:
				bot_user = db.get_user(username=args.username)
				if bot_user:
					utils.make_error(command, content="{} is already a bot user. Nothing to do.".format(args.username))
				else:
					db.useradd(
						id=user["id"],
						username=args.username,
						password=self.__rsa_encrypt(self.default_user_passwd),
						level=args.level,
					)
					utils.make_success(command, content="{} was added to the bot with user level {}.".format(args.username, args.level))
			else:
				utils.make_error(command, content="Slack user {} not found.".format(args.username))
		else:
			utils.make_error(command, content=["Invalid input.", "Usage: {}".format(command.command["usage"])])

	def userdel(self, command=None):
		if command:
			username = command.command_args
			if username:
				me = command.user["username"]
				if username == me:
					utils.make_error(command, content="userdel suicide is not allowed.")
				else:
					bot_user = db.get_user(username=username)
					if bot_user:
						db.userdel(username=username)
						# Validate by reloading the user
						utils.make_success(command, content="{} was deleted from the bot.".format(username))
					else:
						utils.make_error(command, content="{} is not a bot user. Nothing to do.".format(username))
			else:
				utils.make_error(command, content=["No username specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def userreset(self, command=None):
		if command:
			username = command.command_args
			if username:
				me = command.user["username"]
				if username == me:
					utils.make_error(command, content="userrest suicide is not allowed.")
				else:
					bot_user = db.get_user(username=username)
					if bot_user:
						db.userreset(username=username)
						# Validate by reloading the user
						utils.make_success(command, content="{} was successfully reset.".format(username))
					else:
						utils.make_error(command, content="{} is not a bot user. Nothing to do.".format(username))
			else:
				utils.make_error(command, content=["No username specified.", "Usage: {}".format(command.command["usage"])])
		else:
			utils.make_error(command, content="An unknown error has occurred.")


	def users(self, command=None):
		if command:
			users = db.users()
			if len(users) <= 0:
				utils.make_error(command, "No users found. That doesn't seem right.")
			else:
				messages = []
				formatter = "{:12}{:20}{:<10}{:<20}{:<15}{:<10}{:<25}"
				header = formatter.format("ID", "Username", "Level", "Last Login", "Failed Logins", "Locked", "Must Change Password")
				divider = "=" * len(header)
				messages.append(header)
				messages.append(divider)
				for user in users:
					messages.append(formatter.format(
						user["id"],
						user["username"],
						user["level"],
						user["last_auth"],
						user["failed_logins"],
						user["locked"],
						user["must_change_pw"]
					))
				utils.make_success(command, content=messages)
		else:
			utils.make_error(command, content="An unknown error has occurred.")

	def __rsa_encrypt(self, message):	
		message = message.encode("utf-8")
		key = RSA.importKey(open(self.bot.config["public_key"]).read())
		cipher = PKCS1_OAEP.new(key)
		ciphertext = cipher.encrypt(message)
		return b64encode(ciphertext).decode("utf-8")

	def __rsa_decrypt(self, ciphertext):
		ciphertext = b64decode(ciphertext)
		try:
			key = RSA.importKey(open(self.bot.config["private_key"]).read(), passphrase=self.bot.config["encryption_key"])
			cipher = PKCS1_OAEP.new(key)
			message = cipher.decrypt(ciphertext).decode("utf-8")
			return message
		except:
			return None

	def __setup_methods(self):
		return {
			"auth": {
				"usage": "auth <password> -- Authenticate with the bot.",
				"level": 0,
				"type": "private",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"deauth": {
				"usage": "deauth -- Clear session data from the users database.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"disable": {
				"usage": "disable <command> -- Disable a command.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"disablemod": {
				"usage": "disablemod <plugin> -- Disable <plugin> and all its commands. Example: disablemod swagbot.plugins.intuit",
				"level": 90,
				"type": "all",
				"can_be_disabled": 1,
				"hidden": 0,
				"monospace": 0,
			},
			"enable": {
				"usage": "enable <command> -- Enable a command.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"enablemod": {
				"usage": "enablemod <plugin> -- Enable <plugin> and all its commands.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 1,
				"hidden": 0,
				"monospace": 0,
			},
			"greeting": {
				"usage": "greeting [<language>] -- Learn how to greet someone in a random language or specify a language to see how to greet someone.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"help": {
				"usage": "help [<command>] -- Display a list of commands or usage for a specific command.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 1,

			},
			"hepl": {
				"usage": "help [<command>] -- Display a list of commands or usage for a specific command.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 1,
				"monospace": 1,
				"method": "help",
			},
			"hide": {
				"usage": "hide <command> -- Hide <command> from help. You should never need to do this.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"login": {
				"usage": "login <password> -- Login to the bot.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 0,
				"method": "auth",
				"hidden": 0,
				"monospace": 0,
			},
			"logout": {
				"usage": "logout -- Log out of the bot.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 0,
				"method": "deauth",
				"hidden": 0,
				"monospace": 0,
			},
			"passwd": {
				"usage": "passwd <old_passwd> <new_passwd> -- Change your bot password.",
				"level": 0,
				"type": "private",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"rac": {
				"usage": "rac -- Refresh the account cache.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 1,
				"method": "refresh_account_cache",
				"hidden": 1,
				"monospace": 0,
			},
			"reload": {
				"usage": "reload -- Reload all configured plugins. Experimental.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 1,
			},
			"time": {
				"usage": "time -- Displays the current time in UTC format.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 1,
				"hidden": 0,
				"monospace": 0,
			},
			"unhide": {
				"usage": "unhide <command> -- Unhide <command> from help. You should never need to do this.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"uptime": {
				"usage": "uptime -- Displays the bot's uptime.",
				"level": 0,
				"type": "all",
				"can_be_disabled": 1,
				"hidden": 0,
				"monospace": 0,
			},
			"useradd": {
				"usage": "useradd <username> <level> -- Add a valid Slack user to the users table. Example: useradd akumar 10",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"userdel": {
				"usage": "userdel <username> -- Remove a user from the users table.",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"userreset": {
				"usage": "userreset <username> -- Reset a user's flags (last failed login, lock status, etc).",
				"level": 90,
				"type": "all",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 0,
			},
			"users": {
				"usage": "users -- Display a list of users.",
				"level": 80,
				"type": "private",
				"can_be_disabled": 0,
				"hidden": 0,
				"monospace": 1,
			},
		}
