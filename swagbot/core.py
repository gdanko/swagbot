from pprint import pprint, pformat
import inspect
import json
import swagbot.database as db
import swagbot.utils as utils
import re
import sys
import time

class Event(object):
	def __init__(self, **kwargs):
		self.success = True
		global logger
		classname = utils.classname(self)
		debug = kwargs["debug"] if ("debug" in kwargs and isinstance(kwargs["debug"], bool)) else False
		logger = utils.configure_logger(loggerid=classname, debug=debug)
		event = kwargs["event"]
		event_class = utils.classname(event)
		lomond_classes = ["Closed", "Closing", "Connected", "ConnectFail", "Connecting", "Disconnected",
			"Ping", "Poll", "Pong", "Ready", "Rejected", "Text", "UnknownMessage"]
		valid_classes = ["lomond.events.{}".format(c) for c in lomond_classes]

		if not event_class in valid_classes:
			logger.fatal("An invalid lomond event was passed. The object is of type \"{}\".".format(event_class))
			sys.exit()

		self.type = event.__class__.__name__
		self.time = now()

		if self.type == "Connecting":
			self.url = event.url
			self.body = "Connecting to {}".format(event.url)

		elif self.type == "ConnectFail":
			self.success = False
			self.reason = event.reason
			self.body = self.reason

		elif self.type == "Rejected":
			self.success = False
			self.response = event.response
			self.reason = event.reason
			self.body = self.reason

		elif self.type == "Connected":
			self.body = "Successfully connected"

		elif self.type == "Ready":
			self.response = event.response
			self.protocol = event.protocol
			self.extensions = event.extensions
			self.body = event.response

		if self.type == "Text":
			#if "subtype" in event_text and event_text["subtype"] == "message_changed":
			body = utils.validate_json(event.text)
			if body:
				if "ok" in body and body["ok"] == False:
					self.success = False

				if "type" in body and body["type"] == "message":
					if "channel" in body:
						if re.search("^D", body["channel"]):
							body["message_type"] = "private"
						elif re.search("^C", body["channel"]):
							body["message_type"] = "public"

				# Handle edited messages
				if "subtype" in body and body["subtype"] == "message_changed":
					body["text"] = body["message"]["text"]
					body["user"] = body["message"]["user"]

				self.body = body
			else:
				self.body = event.text


			self.type = self.body["type"] if "type" in self.body else "unknown"

		elif self.type == "Disconnected":
			self.graceful = event.graceful
			self.success = self.graceful
			self.reason = event.reason
			if self.graceful == True:
				self.body = "The websocket disconnected gracefully."
			else:
				self.success = False
				self.body = "The websocket disconnected unexpectedly: {}".format(self.reason)

		elif self.type == "Closing":
			self.code = event.code
			self.reason = event.reason
			self.body = "The websocket is closing: {}".format(self.reason)

		elif self.type == "Closed":
			self.code = event.code
			self.reason = event.reason
			self.body = "The websocket closed: {}".format(self.reason)

		elif self.type == "Poll":
			self.body = "websocket poll."

		elif self.type == "Ping":
			self.data = event.data
			self.body = "websocket ping"

		elif self.type == "Pong":
			self.data = event.data
			self.body = "websocket pong"

class Command(object):
	def __init__(self, **kwargs):
		global logger
		classname = utils.classname(self)
		debug = kwargs["debug"] if ("debug" in kwargs and isinstance(kwargs["debug"], bool)) else False
		logger = utils.configure_logger(loggerid=classname, debug=debug)
		self.success = None
		self.response = {"status": "success", "messages": ["No message received from the bot."]}
		self.bot = kwargs["bot"]
		self.event = kwargs["event"]
		self.command = kwargs["command"]
		self.command_args = kwargs["command_args"] if "command_args" in kwargs else None
		self.argv = kwargs["argv"] if "argv" in kwargs else None
		self.user = db.get_user(id=self.event["user"])
		self.__validate_command()

	def __validate_command(self):
		session_timeout = 3600
		now = int(time.time())
		if self.user:
			user_last_auth = self.user["last_auth"] if "last_auth" in self.user else 0
			user_level = self.user["level"] if "level" in self.user else 0
			user_locked = self.user["locked"] if "locked" in self.user else True
			user_must_change_pw = self.user["must_change_pw"] if "must_change_pw" in self.user else True
		command_enabled = self.command["enabled"] if "enabled" in self.command else False
		command_level = self.command["level"] if "level" in self.command else 0
		command_name = self.command["name"] if "name" in self.command else None
		command_module = self.command["module"] if "module" in self.command else None
		command_method = self.command["method"] if "method" in self.command else None
		command_type = self.command["type"] if "type" in self.command else None
		message_type = self.event["message_type"] if "message_type" in self.event else None
		errors = []

		if command_name:
			if command_enabled == True:
				if command_type == "public" and message_type == "private":
					errors.append("The command \"{}\" cannot be used in private.".format(command_name))
				elif command_type == "private" and message_type == "public":
					errors.append("The command \"{}\" cannot be used in public.".format(command_name))
				else:
					if command_level > 0:
						if self.user:
							if user_locked == True:
								errors.append("Your account is currently locked. Please contact a bot administrator.")

							if command_name != "passwd" and user_must_change_pw == True:
								errors.append("You must change your password with \"passwd\" before using {}.".format(command_name))

							if user_level < command_level:
								errors.append("You do not have permission to execute {}.".format(command_name))

							if command_name != "auth" and (now - user_last_auth) > session_timeout:
								errors.append("Your session has expired. Please authenticate with \"auth\".")

						else:
							errors.append("Failed to get user data. Cannot execute command.")
			else:
				errors.append("The command \"{}\" is not currently enabled.".format(command_name))
		else:
			errors.append("The command \"{}\" was not found. This is a fatal error.".format(command_name))
		
		if len(errors) > 0:
			utils.make_error(self, content=errors)
		else:

			bot_command = getattr(self.bot.plugins[command_module]["instance"], command_method)
			bot_command(command=self)

class BasePlugin(object):
	def __init__(self, bot):
		self.logger = utils.configure_logger()
		self.session_timeout = 3600
		self.classname = self.__class__.__module__.split(".")[-1]

		if not bot:
			raise exception.MissingConstructorParameter(classname=self.classname, parameter="bot")

		bot_type = utils.classname(bot)
		if bot_type == "swagbot.bot.SwagBot":
			self.bot = bot
		else:
			raise exception.NotASwagBotObject(classname=self.classname, got=bot_type)

def whoami():
	return inspect.stack()[1][3]

def whosmydaddy():
	return inspect.stack()[2][3]

def now():
	return time.time()