class MissingConstructorParameter(Exception):
	def __init__(self, classname=None, parameter=None):
		self.classname = classname
		self.parameter = parameter
		return

	def __str__(self):
		self.error = "The required \"{}\" parameter is missing from the {} constructor.".format(self.parameter, self.classname)
		return self.error

class ConfigFileRead(Exception):
	def __init__(self, path=None, message=None):
		self.path = path
		self.message = message
		return

	def __str__(self):
		self.error = "An error occurred when reading the SwagBot configuration file \"{}\": {}".format(self.path, self.message)
		return self.error

class InvalidConfigFile(Exception):
	def __init__(self, path=None, message=None):
		self.path = path
		self.message = message
		return

	def __str__(self):
		self.error = "The specified config file \"{}\" is invalid: {}".format(self.path, self.message)
		return self.error

class InvalidJsonError(Exception):
	def __init__(self, status_code=None, body=None):
		self.status_code = status_code
		self.body = body if body else "No HTML body returned"
		return

	def __str__(self):
		return "Invalid JSON was received from the Slack server. Status code {}; HTML body: {}.".format(self.status_code, self.body)

class WebSocketConnectionFailed(Exception):
	def __init__(self, message=None):
		self.message = message
		return

	def __str__(self):
		self.error = "The websocket connection failed with the following error: {}.".format(self.message)
		return self.error

class WebSocketUpgradeRejected(Exception):
	def __init__(self, message=None):
		self.message = message
		return

	def __str__(self):
		self.error = "I was able to connect to the websocket but upgrade failed with the following error: {}.".format(self.message)
		return self.error

class PopulateDatabaseError(Exception):
	def __init__(self, table=None, message=None):
		self.table = table
		self.message = message
		return

	def __str__(self):
		error = ["Failed to populate the {} table.".format(self.table)]
		if message:
			error.append("The message is: {}".format(self.message))

		self.error = " ".join(error)
		return self.error

class NotASwagBotObject(Exception):
	def __init__(self, classname=None, got=None):
		self.classname = classname
		self.got = got
		return

	def __str__(self):
		self.error = "The class {} requires a valid swagbot.bot.SwagBot object in the constructor. You provided {}.".format(self.classname, self.got)
		return self.error
