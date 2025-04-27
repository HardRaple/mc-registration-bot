#!./.venv/bin/python

import re
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from mcrcon import MCRcon, MCRconException

# Adapters for datetime
def adapt_datetime(dt):
    return dt.isoformat()

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", lambda x: datetime.fromisoformat(x.decode()))

# Configuration
load_dotenv()
RCON_HOST = str(os.environ.get('MC_SERVER_IP'))
RCON_PORT = int(os.environ.get('RCON_PORT'))
RCON_PASSWORD = str(os.environ.get('RCON_PASSWD'))
BOT_TOKEN = str(os.environ.get('BOT_TKN'))

NICKNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,16}$')

# Initialising database with timestamp support
conn = sqlite3.connect(
    'minecraft_bot.db',
    detect_types=sqlite3.PARSE_DECLTYPES
)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS players
             (telegram_id INTEGER PRIMARY KEY,
              minecraft_nick TEXT,
              last_change timestamp)''')
conn.commit()

def validate_nick(nick):
    return bool(NICKNAME_PATTERN.match(nick))

# RCON
def rcon_command(command):
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
            return mcr.command(command)
    except (MCRconException, ConnectionError):
        return None

def is_nick_taken(nick):
    response = rcon_command('minecraft:whitelist list')
    return nick in ([response.lower().split(",")[0].split()[-1]]+response.lower().split(", ")[1:])

def is_banned(telegram_id):
    try:
        cursor.execute('SELECT minecraft_nick FROM players WHERE telegram_id = ?', (telegram_id,))
        result = cursor.fetchone()
        if not result:
            return False
        old_nick = result[0]
        banned = rcon_command(f'essentials:seen {old_nick}')
        return ("- Banned:" in banned)
    except sqlite3.Error:
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Use /register [nickname] to register")

async def register_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        args = update.message.text.split()

        if len(args) < 2:
            await update.message.reply_text("Use: /register [nickname]")
            return

        new_nick = args[1]

        if not validate_nick(new_nick):
            await update.message.reply_text("❌ Incorrect nickname! Allowed symbols: letters A-Z, numbers and _ (3-16 symbols)")
            return

        cursor.execute('SELECT * FROM players WHERE telegram_id = ?', (user_id,))
        if cursor.fetchone():
            await update.message.reply_text("You are already registered! Use /change_nick [new_nickname] to change")
            return

        if is_nick_taken(new_nick):
            await update.message.reply_text("⚠️ This nickname is already taken")
            return

        if rcon_command(f'minecraft:whitelist add {new_nick}') is None:
            raise Exception()

        cursor.execute('INSERT INTO players VALUES (?, ?, ?)',
                      (user_id, new_nick, datetime.now().isoformat()))
        conn.commit()
        await update.message.reply_text("✅ Registration successful!")

    except Exception as e:
        await update.message.reply_text("An error has occured. Try again later")
        print(e)

async def change_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        args = update.message.text.split()

        if len(args) < 2:
            await update.message.reply_text("Use: /change_nick [new_nickname]")
            return

        new_nick = args[1]

        if not validate_nick(new_nick):
            await update.message.reply_text("❌ Incorrect nickname! Allowed symbols: letters A-Z, numbers and _ (3-16 symbols)")
            return

        if is_banned(user_id):
            await update.message.reply_text("🚫 Nickname change is not available")
            return

        cursor.execute('SELECT last_change FROM players WHERE telegram_id = ?', (user_id,))
        result = cursor.fetchone()
        if result and (datetime.now() - result[0]) < timedelta(hours=24):
            await update.message.reply_text("Nickname change is available once every 24 hours")
            return

        if is_nick_taken(new_nick):
            await update.message.reply_text("⚠️ This nickname is already taken")
            return

        cursor.execute('SELECT minecraft_nick FROM players WHERE telegram_id = ?', (user_id,))
        old_nick = cursor.fetchone()[0]

        if rcon_command(f'minecraft:whitelist remove {old_nick}') is None:
            raise Exception()

        if rcon_command(f'minecraft:whitelist add {new_nick}') is None:
            raise Exception()

        cursor.execute('UPDATE players SET minecraft_nick = ?, last_change = ? WHERE telegram_id = ?',
                      (new_nick, datetime.now().isoformat(), user_id))
        conn.commit()
        await update.message.reply_text("✅ Nickname successfully changed!")

    except Exception as e:
        await update.message.reply_text("An error has occured. Try again later")
        print(e)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('register', register_nick))
    application.add_handler(CommandHandler('change_nick', change_nick))

    application.run_polling()

if __name__ == '__main__':
    main()
