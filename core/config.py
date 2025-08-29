import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# === НОВАЯ СИСТЕМА РОЛЕЙ ===

# BOSS - полный доступ ко всему (только самые главные)
BOSS_ID_STR = os.getenv("BOSS_ID", "")
if BOSS_ID_STR:
    BOSS_IDS = [int(id.strip()) for id in BOSS_ID_STR.replace(',', ' ').split() if id.strip().isdigit()]
    BOSS_ID = BOSS_IDS[0] if BOSS_IDS else None  # Основной босс для обратной совместимости
else:
    BOSS_IDS = []
    BOSS_ID = None

# ADMIN - доступ к админке + отправка броней
ADMIN_ID_STR = os.getenv("ADMIN_IDS", "")
if ADMIN_ID_STR:
    ADMIN_IDS_LIST = [int(id.strip()) for id in ADMIN_ID_STR.replace(',', ' ').split() if id.strip().isdigit()]
else:
    ADMIN_IDS_LIST = []

# SMM - только отправка броней (для СММщиков)
SMM_ID_STR = os.getenv("SMM_IDS", "")
if SMM_ID_STR:
    SMM_IDS = [int(id.strip()) for id in SMM_ID_STR.replace(',', ' ').split() if id.strip().isdigit()]
else:
    SMM_IDS = []

# Объединенные списки для удобства проверки
ALL_ADMINS = BOSS_IDS + ADMIN_IDS_LIST  # Кто имеет доступ к админке
ALL_BOOKING_STAFF = BOSS_IDS + ADMIN_IDS_LIST + SMM_IDS  # Кто может отправлять брони

# Старая переменная ADMIN_IDS для обратной совместимости
ADMIN_IDS = ALL_ADMINS

# === ЧАТЫ ДЛЯ УВЕДОМЛЕНИЙ ===

# Основной чат для отчетов (старая переменная для обратной совместимости)
REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID")

# Специализированные чаты
BOOKING_NOTIFICATIONS_CHAT_ID = -1002655754865  # Чат для заявок на бронирование
NASTOYKA_NOTIFICATIONS_CHAT_ID = -1002813620544  # Чат для уведомлений о настойках (отчеты, купоны)

# --- Google Sheets ---
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")  # Основная таблица
GOOGLE_SHEET_KEY_SECONDARY = os.getenv("GOOGLE_SHEET_KEY_SECONDARY")  # Дополнительная таблица
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

# PostgreSQL
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_DB = os.getenv("POSTGRES_DB", "railway")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Если DATABASE_URL не задан, формируем его из отдельных переменных
if not DATABASE_URL and all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB]):
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    print(f"✅ Сформирован DATABASE_URL из отдельных переменных PostgreSQL")

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
