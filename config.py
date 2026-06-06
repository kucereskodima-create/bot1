import os
from aiogram import Bot

API_TOKEN = os.environ.get("BOT_TOKEN", "")
owners   = [int(x) for x in os.environ.get("BOT_OWNERS",       "0").split(",") if x.strip().isdigit()]
admins   = [int(x) for x in os.environ.get("BOT_ADMINS",       "7791816738").split(",") if x.strip().isdigit()]
founders = [int(x) for x in os.environ.get("BOT_FOUNDERS",     "0").split(",") if x.strip().isdigit()]
bot = Bot(token=API_TOKEN)
