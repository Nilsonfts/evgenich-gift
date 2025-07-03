# config.py
import os

# Токен вашего бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID вашего телеграм-канала
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ GOOGLE SHEETS ---
GOOGLE_SHEET_KEY = "1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs"
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")


# Проверки, что переменные загружены
if not BOT_TOKEN:
    raise ValueError("Не найдена переменная окружения BOT_TOKEN!")
if not CHANNEL_ID:
    raise ValueError("Не найдена переменная окружения CHANNEL_ID!")
if not GOOGLE_CREDENTIALS_JSON:
    raise ValueError("Не найдена переменная окружения GOOGLE_CREDENTIALS_JSON!")
