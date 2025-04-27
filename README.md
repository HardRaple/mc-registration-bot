# mc-registration-bot
Telegram bot for managing whitelist of players on minecraft server

## Requirements
* Python 3.12 or higher
* python-telegram-bot, sqlite3, mcrcon, dotenv
* Configured RCON on minecraft server
* Essentials minecraft plugin (only main file required)

## Usage
* Create .venv and install necessary libraries
* Put your minecraft server ip, RCON port, RCON password and bot token in .env file, here's an example:
```
MC_SERVER_IP="127.0.0.1"
RCON_PORT="25575"
RCON_PASSWD="VeryStrongPassword"
BOT_TKN="token"
```
* launch mc_reg_bot.py