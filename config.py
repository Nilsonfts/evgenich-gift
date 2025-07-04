# config.py
import os

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- Google Sheets ---
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# --- Стикеры ---
HELLO_STICKER_ID = os.getenv("HELLO_STICKER_ID")
NASTOYKA_STICKER_ID = os.getenv("NASTOYKA_STICKER_ID")
THANK_YOU_STICKER_ID = os.getenv("THANK_YOU_STICKER_ID") # Новая переменная

# --- Проверки ---
if not all([
    BOT_TOKEN, 
    CHANNEL_ID, 
    GOOGLE_SHEET_KEY, 
    GOOGLE_CREDENTIALS_JSON, 
    HELLO_STICKER_ID, 
    NASTOYKA_STICKER_ID,
    THANK_YOU_STICKER_ID # Новая переменная в проверке
]):
    raise ValueError("Одна или несколько переменных окружения не установлены! Проверь все, включая все ID стикеров.")
