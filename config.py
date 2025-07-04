import os

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOSS_ID_STR = os.getenv("BOSS_ID", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in BOSS_ID_STR.split(',') if admin_id.strip()]
REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID")

# --- Google Sheets ---
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# --- Стикеры ---
HELLO_STICKER_ID = os.getenv("HELLO_STICKER_ID")
NASTOYKA_STICKER_ID = os.getenv("NASTOYKA_STICKER_ID")
THANK_YOU_STICKER_ID = os.getenv("THANK_YOU_STICKER_ID")
FRIEND_BONUS_STICKER_ID = os.getenv("FRIEND_BONUS_STICKER_ID") 

# --- Ссылки ---
MENU_URL = os.getenv("MENU_URL")

# --- Проверки ---
if not all([
    BOT_TOKEN, CHANNEL_ID, GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON, 
    HELLO_STICKER_ID, NASTOYKA_STICKER_ID, THANK_YOU_STICKER_ID, ADMIN_IDS, 
    REPORT_CHAT_ID, MENU_URL
]):
    raise ValueError("Одна или несколько переменных окружения не установлены! Проверь все.")
