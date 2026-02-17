import os
import json
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Вспомогательная функция для парсинга JSON из многострочных строк (Railway raw editor)
def _parse_json_safe(json_string):
    """Парсит JSON из строки, обрабатывая многострочные и однострочные форматы."""
    if not json_string:
        return None
    try:
        # Пытаемся парсить как есть и вернуть словарь
        return json.loads(json_string)
    except (json.JSONDecodeError, ValueError):
        # Если не сработало, пытаемся разбить по переносам и переконструировать
        try:
            # Убираем лишние переносы и пробелы в начале/конце строк
            cleaned = " ".join(line.strip() for line in json_string.splitlines() if line.strip())
            return json.loads(cleaned)
        except Exception:
            return None

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@evgenichbarspb")  # СПб канал (по умолчанию)
CHANNEL_ID_MSK = os.getenv("CHANNEL_ID_MSK", "@evgenichmoscow")  # Москва канал

# === НОВАЯ СИСТЕМА РОЛЕЙ ===
# Теперь роли также можно управлять через админ-панель (web/admin_config/staff.json)
# Переменные окружения используются как фоллбэк

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

# Функция для получения ролей с учетом админ-панели
def get_all_roles():
    """Получить все роли с учетом админ-панели и переменных окружения"""
    try:
        from core.admin_config import get_staff
        staff = get_staff()
        
        # Объединяем ID из админ-панели и переменных окружения
        bosses = [u['id'] for u in staff.get('bosses', [])] + BOSS_IDS
        admins = [u['id'] for u in staff.get('admins', [])] + ADMIN_IDS_LIST
        smm = [u['id'] for u in staff.get('smm', [])] + SMM_IDS
        
        return {
            'bosses': list(set(bosses)),
            'admins': list(set(admins)),
            'smm': list(set(smm))
        }
    except:
        # Фоллбэк на переменные окружения
        return {
            'bosses': BOSS_IDS,
            'admins': ADMIN_IDS_LIST,
            'smm': SMM_IDS
        }

# Объединенные списки для удобства проверки (с учетом админ-панели)
def _get_combined_lists():
    roles = get_all_roles()
    return (
        roles['bosses'] + roles['admins'],  # ALL_ADMINS
        roles['bosses'] + roles['admins'] + roles['smm']  # ALL_BOOKING_STAFF
    )

ALL_ADMINS, ALL_BOOKING_STAFF = _get_combined_lists()

# Старая переменная ADMIN_IDS для обратной совместимости
ADMIN_IDS = ALL_ADMINS

# === ЧАТЫ ДЛЯ УВЕДОМЛЕНИЙ ===

# Основной чат для отчетов (старая переменная для обратной совместимости)
REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID")

# Специализированные чаты
BOOKING_NOTIFICATIONS_CHAT_ID = -1002655754865  # Чат для заявок на бронирование (СПБ)
BOOKING_NOTIFICATIONS_CHAT_ID_MSK = -1003120803112  # Чат для заявок на бронирование (МСК)
NASTOYKA_NOTIFICATIONS_CHAT_ID = -1002813620544  # Чат для уведомлений о настойках (отчеты, купоны)

# --- Google Sheets ---
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")  # Основная таблица
GOOGLE_SHEET_KEY_SECONDARY = os.getenv("GOOGLE_SHEET_KEY_SECONDARY")  # Дополнительная таблица

# Обработка GOOGLE_CREDENTIALS_JSON: поддержка многострочного JSON из Railway raw editor
_raw_creds = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CREDENTIALS_JSON = _parse_json_safe(_raw_creds) if _raw_creds else None

# --- Нейросеть (Новое) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Стикеры ---
HELLO_STICKER_ID = os.getenv("HELLO_STICKER_ID")
NASTOYKA_STICKER_ID = os.getenv("NASTOYKA_STICKER_ID")
THANK_YOU_STICKER_ID = os.getenv("THANK_YOU_STICKER_ID")
FRIEND_BONUS_STICKER_ID = os.getenv("FRIEND_BONUS_STICKER_ID")

# --- GetMeBack (GMB) система лояльности ---
GMB_API_KEY = os.getenv("GMB_API_KEY", "")
GMB_API_URL = os.getenv("GMB_API_URL", "https://evgenich.getmeback.ru/rest/base/v33/validator/")
GMB_SPASIBO_BOT_TOKEN = os.getenv("GMB_SPASIBO_BOT_TOKEN", "")  # Токен @spasibo_EVGENICH_bot

# --- Ссылки ---

# --- База данных ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/evgenich_data.db")

# PostgreSQL
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() in ("true", "1", "yes")
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

def get_channel_id_for_user(source: str) -> str:
    """
    Определяет какой канал использовать для проверки подписки по источнику пользователя.
    
    Args:
        source: Источник регистрации пользователя
        
    Returns:
        str: ID канала (@evgenich_bar или @evgenichmoscow)
    """
    # Если источник содержит МСК или заканчивается на _msk - московский канал
    if source and ('МСК' in source or source.endswith('_msk')):
        return CHANNEL_ID_MSK
    return CHANNEL_ID

# Опциональные переменные с дефолтными значениями
if not GOOGLE_SHEET_KEY:
    print("⚠️  GOOGLE_SHEET_KEY не установлен - экспорт в Google Sheets отключен")
if not GOOGLE_CREDENTIALS_JSON:
    print("⚠️  GOOGLE_CREDENTIALS_JSON не установлен или невалиден - экспорт в Google Sheets отключен")
if not OPENAI_API_KEY:
    print("⚠️  OPENAI_API_KEY не установлен - AI функции отключены")
if not REPORT_CHAT_ID:
    print("⚠️  REPORT_CHAT_ID не установлен - отчеты не будут отправляться")
if GMB_API_KEY:
    print(f"✅ GetMeBack: API подключён ({GMB_API_URL[:40]}...)")
else:
    print("⚠️  GMB_API_KEY не установлен — система лояльности GetMeBack отключена")

# Логирование статуса подключений
print(f"✅ PostgreSQL: {'Включен (DATABASE_URL установлен)' if USE_POSTGRES and DATABASE_URL else 'Отключен или неполная конфигурация'}")
print(f"✅ Google Sheets: {'Включен' if GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON else 'Отключен'}")
