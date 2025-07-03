# config.py
import os

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- Google Sheets ---
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# --- Проверки ---
if not all([BOT_TOKEN, CHANNEL_ID, GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON]):
    raise ValueError("Одна или несколько переменных окружения не установлены!")
