# SwagBot
SwagBot is an information bot for Slack. It utilizes Slack's RTM API to interact with users and provide sometimes useful information.

# Installation
Coming soon

# Features
SwagBot possesses a number of useful features, some of which set it apart from other availble bots.

* SwagBot utilizes a SQLite backend for a number of things such as
  * User database.
  * Command definitions (command enabled, etc)
  * Module definitions for enabling and disabling modules.
  * Quotes used in commands such as `fortune` and `yomama`.
* Full authentication system includes:
  * Passwords encrypted with 2048 bit encryption key.
  * Configurable session timeout.
  * Passwords locked after three failed logins.
* SwagBot uses a plugin-based architecture for its commands. i.e., Commands are stored in Python modules which are subclasses of the class `iris.core.BasePlugin`. Because of the modularity, commands or entire plugins can be enabled/disabled on the fly.
* SwagBot is resilient. If there is an unexpected error and the websocket disconnects, the bot will attempt to reconnect. This also applies for a code error which causes the bot or one of its modules to crash.
* New code can be added without taking the bot down. You can simply instruct the bot to reload its plugins.

# Classes
### swagot.bot.SwagBot
This is the main bot class. It initializes the bot, loads the plugins, and launches required threads. It also processes inbound events.
### swagbot.core.Event
Every event that is received by the websocket creates a new `swagbot.core.Event` object. The object contains information about the received event so that the bot knows how to process it.
### swagbot.core.Command
If a user says something to the bot that is actually a bot command, its Event object is used to construct a Command object. The command object determines if the command is able to be executed based on factors like command level, user level, and command state. The command output is also stored in the command object. It allows the bot to process each command in an encapsulated object.

