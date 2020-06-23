from lomond import WebSocket
from pprint import pprint, pformat
from swagbot.core import Event,Command
import importlib
import inspect
import json
import os
import pkgutil
import psutil
import re
import signal
import swagbot.database as db
import swagbot.exception as exception
import swagbot.plugins
import swagbot.request as request
import swagbot.utils as utils
import sys
import threading
import time

PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))

class SwagBot(object):
	def __init__(self, **kwargs):
		self.time_init = utils.now()
		self.success = None
		self.classname = utils.classname(self)
		self.debug = kwargs["debug"] if ("debug" in kwargs and isinstance(kwargs["debug"], bool)) else False
		self.logger = utils.configure_logger(loggerid=self.classname, debug=self.debug)
		self.die_if_running()
		self.go_away = False

		if not "config_file" in kwargs:
			raise exception.MissingConstructorParameter(classname=self.classname, parameter="config_file")

		self.config = utils.parse_config(config_file=kwargs["config_file"])
		self.api_endpoint = self.config["slack_endpoint"]
		# parse_config needs to adequately parse the config file. right now it does not.
		self.token = self.config["slack_token"]
		self.initialize_bot()

	def initialize_bot(self):
		self.start_time = utils.now()
		self.authenticate()

	def authenticate(self):
		uri = "https://slack.com/api/rtm.connect" #?token={}".format(self.token)
		headers = {"Authorization": "Bearer {}".format(self.token)}
		request.post(self, uri=uri, extra_headers=headers)
		if self.success:
			if "url" in self.response:
				websocket_url = self.response["url"]
				self.load_plugins()
				self.populate_account_cache()
				self.start_bot(uri=websocket_url)
		else:
			pprint(self.response)
			sys.exit(1)

	def load_plugins(self):
		# https://packaging.python.org/guides/creating-and-discovering-plugins/
		# Make sure there is a Plugin class and that it is subclassed from BasePlugin
		self.plugins = {}

		def iter_namespace(namespace_package):
			return pkgutil.iter_modules(namespace_package.__path__, namespace_package.__name__ + ".")

		# Load all built-ins
		for finder, name, ispkg in iter_namespace(swagbot.plugins):
			module_name = name.split(".")[-1]
			if module_name in self.plugins:
				self.logger.warn("Could not load the module \"{}\" as a module with the same name is already loaded.".format(module_name))
			else:
				module = db.get_module(module=module_name)
				if module:
					if module["enabled"] == 1:
						self.logger.info("Loading module {}.".format(module_name))
						module_obj = importlib.import_module(name)
						module_instance = module_obj.Plugin(bot=self)
						#db.update_plugin_commands(module=self.classname, methods=self.methods)
						self.logger.info("Updating bot commands for the module {}.".format(module_name))
						db.update_plugin_commands(module=module_instance.classname, methods=module_instance.methods)

						self.plugins[module_name] = {
							"module": utils.classname(module_instance),
							"instance": module_obj.Plugin(bot=self),
						}
					else:
						self.logger.info("Not loading module {} because it is disabled.".format(module_name))
				else:
					self.logger.info("I have found a new module named \"{}\" which is not in the database. I will insert it and leave it disabled.".format(module_name))
					db.moduleadd(module=module_name)
		self.prune_commands_table()

	def populate_account_cache(self):
		# Reports success if token is bad. Fix this.
		self.logger.info("Populating the Slack account cache.")
		headers = {"Authorization": "Bearer {}".format(self.token)}
		request.post(self, uri="{}/users.list".format(self.api_endpoint), extra_headers=headers)
		if self.success:
			self.logger.debug("Populating the Slack account cache.")
			db.populate_account_cache(userlist=self.response)
			self.response = {}

	def prune_commands_table(self):
		loaded_commands = []
		for plugin_name, plugin_obj in self.plugins.items():
			plugin_instance = plugin_obj["instance"]
			loaded_commands += list(plugin_instance.methods.keys())
		loaded_commands = sorted(loaded_commands)

		command_table_commands = db.all_commands()

		to_prune = list(set(command_table_commands) - set(loaded_commands))
		if len(to_prune) > 0:
			command = "command" if len(to_prune) == 1 else "commands"
			self.logger.info("Pruning {} {} from the commands table.".format(len(to_prune), command))
			db.prune_commands_table(commands=to_prune)

	def start_bot(self, uri=None):
		self.websocket = WebSocket(uri)
		self.socket_ready = threading.Event()
		self.event_ready = threading.Event()

		threads = {
			"slack_listener": threading.Thread(name="slack_listener", target=self.socket_run),
			"bot_watcher": threading.Thread(name="slack_listener", target=self.bot_watcher)
		}
		for name, thread in threads.items():
			self.logger.info("Starting thread {}.".format(name))
			thread.start()
		self.socket_ready.set()

		if self.socket_ready.wait(5):
			self.ready_time = time.time()
			self.logger.info("SwagBot ready in {} seconds.".format("{0:.4f}".format(self.ready_time - self.start_time)))

	def bot_watcher(self):
		while self.go_away == False:
			if self.websocket.state.closing == True or self.websocket.state.closed == True:
				self.logger.error("The bot disconnected unexpectedly.. Will try to reconnect in 5 seconds.")
				self.websocket = None
				time.sleep(5)
				self.initialize_bot()
			time.sleep(5)
		self.logger.info("The bot was closed cleanly.")

	def socket_run(self):
		while self.websocket.state.closed == False and self.websocket.state.closing == False:
			for e in self.websocket:
				event = Event(websocket=self.websocket, event=e, debug=self.debug)
				self.logger.debug("New \"{}\" event received: {}".format(event.type, pformat(event.__dict__)))
				if event.type == "Disconnected":
					if event.success == False:
						self.logger.error("The bot disconnected unexpectedly.")
						self.disconnect()
					else:
						self.run_bot = False

				elif event.type == "message":
					self.process_message(event.body)
		self.logger.debug("The state of the websocket is closed or closing. Exiting the event listener thread.")

	def process_message(self, event):
		# sanity check this logic
		# process unknown commands
		text = event["text"]
		matches = re.match("^([^\s]+)(\s+)?(.*)?$", text)
		if matches:
			command_name = matches[1]
			command_args = matches[3] if matches[3] else None
			command = db.command_lookup(command=command_name)
			if command:
				command["name"] = command_name

				# Try to create a sys.argv style set of arguments
				argv = [command_name]
				if command_args:
					argv_pattern = "[^\s\"']+|\"([^\"]*)\"|'([^']*)'"
					for match in re.finditer(argv_pattern, command_args):
						s = match.start()
						e = match.end()
						arg = command_args[s:e]
						arg = re.sub(r'^"|"$', '', arg)
						arg = re.sub(r"^'|'$", '', arg)
						argv.append(arg)

				bot_cmd = Command(bot=self, event=event, command=command, command_args=command_args, argv=argv)
				if bot_cmd.event["message_type"] == "private":
					self.process_private(command=command, bot_cmd=bot_cmd)
				elif bot_cmd.event["message_type"] == "public":
					self.process_public(command=command, bot_cmd=bot_cmd)
		self.event_ready.set()

	def process_private(self, command=None, bot_cmd=None):
		if "messages" in bot_cmd.response:
			channel = bot_cmd.event["channel"]

			if command["monospace"] == True:
				message = "```{}```".format("\n".join(bot_cmd.response["messages"]))
			else:
				message = "{}".format("\n".join(bot_cmd.response["messages"]))
			self.send_message(channel=channel, message=message)

	def process_public(self, command=None, bot_cmd=None):
		if "messages" in bot_cmd.response:
			channel = bot_cmd.event["channel"]
			at = "<@{}>".format(bot_cmd.event["user"])

			if command["monospace"] == True:
				message = "{}```{}```".format(
					at,
					"\n".join(bot_cmd.response["messages"])
				)
			else:
				message = "{} {}".format(
					at,
					"\n".join(bot_cmd.response["messages"])
				)
			self.send_message(channel=channel, message=message)

	def send_message(self, channel=None, message=None):
		self.websocket.send_text(
			json.dumps({
				"id": utils.generate_random(length=16),
				"type": "message",
				"channel": channel,
				"text": message,
			})
		)

	def stop(self):
		self.websocket.close()

	def disconnect(self):
		self.stop()

	def die_if_running(self):
		pid = os.getpid()
		myproc = [proc for proc in psutil.process_iter() if proc._pid == pid][0]
		mycmdline = " ".join(list(myproc.cmdline()))

		bots = []
		for proc in psutil.process_iter():
			try:
				cmdline = " ".join(proc.cmdline())
				if (cmdline == mycmdline) and proc._pid != pid:
					bots.append(proc)
			except:
				pass

		if len(bots) > 0:
			for bot in bots:
				self.logger.fatal("There is a bot running with the pid {}. Cannot start.".format(bot._pid))
			sys.exit(1)

def whoami():
	return inspect.stack()[1][3]

def whosmydaddy():
	return inspect.stack()[2][3]

def now():
	return time.time()
