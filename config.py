# config.py
import os

# Токен вашего бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID вашего телеграм-канала из переменных окружения
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Проверки, что переменные загружены
if not BOT_TOKEN:
    raise ValueError("Не найдена переменная окружения BOT_TOKEN!")
if not CHANNEL_ID:
    raise ValueError("Не найдена переменная окружения CHANNEL_ID!")
