import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOSS_ID_STR = os.getenv("BOSS_ID", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in BOSS_ID_STR.split(',') if admin_id.strip()]
REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID") # <-- Вот эта переменная

# --- Google Sheets ---
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# --- Нейросеть (Новое) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Стикеры ---
HELLO_STICKER_ID = os.getenv("HELLO_STICKER_ID")
NASTOYKA_STICKER_ID = os.getenv("NASTOYKA_STICKER_ID")
THANK_YOU_STICKER_ID = os.getenv("THANK_YOU_STICKER_ID")
FRIEND_BONUS_STICKER_ID = os.getenv("FRIEND_BONUS_STICKER_ID")

# --- Ссылки ---
MENU_URL = os.getenv("MENU_URL")

# --- База данных ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/evgenich_data.db")

# --- Проверки ---
if not all([
    BOT_TOKEN, CHANNEL_ID, ADMIN_IDS,
    HELLO_STICKER_ID, NASTOYKA_STICKER_ID, THANK_YOU_STICKER_ID
]):
    raise ValueError("Основные переменные окружения не установлены! Проверь BOT_TOKEN, CHANNEL_ID, ADMIN_IDS, стикеры.")

# Опциональные переменные с дефолтными значениями
if not GOOGLE_SHEET_KEY:
    print("⚠️  GOOGLE_SHEET_KEY не установлен - экспорт в Google Sheets отключен")
if not GOOGLE_CREDENTIALS_JSON:
    print("⚠️  GOOGLE_CREDENTIALS_JSON не установлен - экспорт в Google Sheets отключен")
if not OPENAI_API_KEY:
    print("⚠️  OPENAI_API_KEY не установлен - AI функции отключены")
if not REPORT_CHAT_ID:
    print("⚠️  REPORT_CHAT_ID не установлен - отчеты не будут отправляться")
if not MENU_URL:
    print("⚠️  MENU_URL не установлен - ссылка на меню не будет работать")
