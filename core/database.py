# database.py
"""
Модуль для управления базой данных (SQLite или PostgreSQL) с асинхронным дублированием в Google Sheets.
"""
import sqlite3
import logging
from typing import Optional, Tuple, List, Dict, Any
import datetime
import pytz
import os
import json
import gspread
import gspread.exceptions
import threading
from collections import defaultdict
from google.oauth2.service_account import Credentials
from .config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON, DATABASE_PATH, USE_POSTGRES, DATABASE_URL

# Импортируем PostgreSQL клиент, если включен режим PostgreSQL
if USE_POSTGRES:
    from db.postgres_client import PostgresClient
    pg_client = PostgresClient()

# --- Вспомогательная функция для парсинга credentials JSON ---
def _parse_credentials_json(creds_str):
    """Парсит JSON из строки (поддерживает многострочный и однострочный форматы)."""
    if not creds_str:
        return None
    # If it's already a dict (config may provide parsed dict), return as is
    if isinstance(creds_str, dict):
        return creds_str
    try:
        return json.loads(creds_str)
    except (json.JSONDecodeError, ValueError):
        try:
            cleaned = " ".join(line.strip() for line in str(creds_str).splitlines() if line.strip())
            return json.loads(cleaned)
        except Exception as e:
            logging.error("Невозможно парсить GOOGLE_CREDENTIALS_JSON: %s", str(e))
            return None

# --- Настройки ---
DB_FILE = DATABASE_PATH  # Используем путь из переменной окружения
SHEET_NAME = "Выгрузка Пользователей"

# Вспомогательная функция форматирования datetime для запросов к БД
def _format_dt_for_db(dt: datetime.datetime) -> str:
    """Возвращает строку для использования в SQLite или PostgreSQL запросах.
    Для PostgreSQL возвращает ISO с timezone; для SQLite возвращает наивную локальную строку 'YYYY-MM-DD HH:MM:SS'.
    """
    if dt is None:
        return None
    try:
        if USE_POSTGRES and pg_client:
            # Для Postgres используем ISO (с tz если есть)
            if dt.tzinfo is None:
                # локализуем в UTC если нет tz
                dt = pytz.utc.localize(dt)
            return dt.isoformat()
        else:
            # Для SQLite приводим к Europe/Moscow и убираем tzinfo
            if dt.tzinfo is not None:
                dt = dt.astimezone(pytz.timezone('Europe/Moscow'))
            return dt.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        # Фоллбэк — isoformat
        return dt.isoformat()

# Проверяем доступность Google Sheets
GOOGLE_SHEETS_ENABLED = bool(GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON)

# --- Функция перевода статусов ---
def _translate_status_to_russian(status: str) -> str:
    """Переводит статус с английского на русский для Google Таблиц."""
    status_translations = {
        'registered': 'Зарегистрирован',
        'issued': 'Купон выдан',
        'redeemed': 'Купон погашен',
        'redeemed_and_left': 'Погашен и отписался'
    }
    return status_translations.get(status, status)

# --- Секция работы с Google Sheets (фоновые задачи) ---
def _get_sheets_worksheet():
    """Подключается к Google Sheets и возвращает рабочий лист."""
    if not GOOGLE_SHEETS_ENABLED:
        logging.warning("Google Sheets отключен - отсутствуют необходимые переменные окружения")
        return None
    try:
        creds_dict = _parse_credentials_json(GOOGLE_CREDENTIALS_JSON)
        if not creds_dict:
            logging.error("G-Sheets | Не удалось парсить GOOGLE_CREDENTIALS_JSON")
            return None
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        
        # Попытка получить лист по названию
        try:
            return spreadsheet.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Лист не найден — логируем доступные и пробуем найти по нечувствительному к регистру
            logging.warning("G-Sheets | Лист '%s' не найден. Ищу среди доступных вкладок:", SHEET_NAME)
            worksheet = None
            for ws in spreadsheet.worksheets():
                logging.warning("G-Sheets |   - %s (id=%s)", ws.title, ws.id)
                if ws.title.strip().lower() == SHEET_NAME.strip().lower():
                    logging.info("G-Sheets | Найдена вкладка по нечувствительному к регистру: %s", ws.title)
                    worksheet = ws
                    break
            
            if not worksheet:
                # Пытаемся создать вкладку
                try:
                    logging.info("G-Sheets | Пытаюсь создать вкладку '%s' автоматически.", SHEET_NAME)
                    new_ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=200, cols=20)
                    logging.info("G-Sheets | Вкладка '%s' успешно создана (id=%s)", SHEET_NAME, new_ws.id)
                    return new_ws
                except Exception as ce:
                    logging.error("G-Sheets | Не удалось создать вкладку '%s': %s", SHEET_NAME, ce)
                    return None
            return worksheet
    except Exception as e:
        logging.error("G-Sheets | Ошибка подключения: %s", str(e))
        return None

def _add_user_to_sheets_in_background(row_data: List[Any]):
    """(Фоновая задача) Добавляет строку с данными пользователя в таблицу (только если пользователя еще нет)."""
    user_id = row_data[1]
    logging.info(f"G-Sheets (фон) | Попытка добавления пользователя {user_id}")
    if not GOOGLE_SHEETS_ENABLED:
        logging.warning(f"G-Sheets (фон) | Google Sheets отключен!")
        return
    try:
        worksheet = _get_sheets_worksheet()
        if not worksheet:
            logging.error(f"G-Sheets (фон) | ❌ Не удалось получить worksheet!")
            return
        
        # Проверяем, существует ли уже пользователь с таким ID
        logging.debug(f"G-Sheets (фон) | Ищу пользователя {user_id} в колонке B...")
        try:
            existing_cell = worksheet.find(str(user_id), in_column=2)
            if existing_cell:
                logging.warning(f"G-Sheets (фон) | ⚠️  Пользователь {user_id} уже в таблице (строка {existing_cell.row}). Пропускаю.")
                return
        except gspread.exceptions.CellNotFound:
            logging.debug(f"G-Sheets (фон) | Пользователь {user_id} не найден - добавляю")
        
        # Добавляем новую строку в конец
        logging.info(f"G-Sheets (фон) | Добавляю новую строку: {row_data}")
        worksheet.append_row(row_data)
        logging.info(f"G-Sheets (фон) | ✅ Пользователь {user_id} добавлен в конец таблицы (новая строка).")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | ❌ Ошибка добавления пользователя {user_id}: {e}", exc_info=True)

def _update_contact_in_sheets_in_background(user_id: int, phone_number: str, contact_shared_date: datetime.datetime):
    """(Фоновая задача) Обновляет контактную информацию пользователя в таблице."""
    if not GOOGLE_SHEETS_ENABLED:
        return
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            cell = worksheet.find(str(user_id), in_column=2)
            if cell:
                worksheet.update_cell(cell.row, 5, phone_number)  # Колонка E - номер телефона
                logging.info(f"G-Sheets (фон) | Контакт пользователя {user_id} успешно обновлен: {phone_number}")
            else:
                logging.warning(f"G-Sheets (фон) | Не удалось найти пользователя {user_id} для обновления контакта.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка обновления контакта для {user_id}: {e}")

def _update_name_in_sheets_in_background(user_id: int, real_name: str):
    """(Фоновая задача) Обновляет настоящее имя пользователя в таблице."""
    if not GOOGLE_SHEETS_ENABLED:
        return
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            cell = worksheet.find(str(user_id), in_column=2)
            if cell:
                worksheet.update_cell(cell.row, 6, real_name)  # Колонка F - настоящее имя
                logging.info(f"G-Sheets (фон) | Имя пользователя {user_id} успешно обновлено: {real_name}")
            else:
                logging.warning(f"G-Sheets (фон) | Не удалось найти пользователя {user_id} для обновления имени.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка обновления имени для {user_id}: {e}")

def _update_birth_date_in_sheets_in_background(user_id: int, birth_date: str):
    """(Фоновая задача) Обновляет дату рождения пользователя в таблице."""
    if not GOOGLE_SHEETS_ENABLED:
        return
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            cell = worksheet.find(str(user_id), in_column=2)
            if cell:
                worksheet.update_cell(cell.row, 7, birth_date)  # Колонка G - дата рождения
                logging.info(f"G-Sheets (фон) | Дата рождения пользователя {user_id} успешно обновлена: {birth_date}")
            else:
                logging.warning(f"G-Sheets (фон) | Не удалось найти пользователя {user_id} для обновления даты рождения.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка обновления даты рождения для {user_id}: {e}")

def _update_status_in_sheets_in_background(user_id: int, new_status: str, redeem_time: Optional[datetime.datetime]):
    """(Фоновая задача) Обновляет статус пользователя в таблице."""
    if not GOOGLE_SHEETS_ENABLED:
        return
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            cell = worksheet.find(str(user_id), in_column=2)
            if cell:
                russian_status = _translate_status_to_russian(new_status)
                worksheet.update_cell(cell.row, 8, russian_status)  # Статус в колонке H (8)
                if redeem_time:
                    worksheet.update_cell(cell.row, 11, redeem_time.strftime('%Y-%m-%d %H:%M:%S'))  # Дата погашения в колонке K (11)
                logging.info(f"G-Sheets (фон) | Статус пользователя {user_id} успешно обновлен на '{russian_status}'.")
            else:
                logging.warning(f"G-Sheets (фон) | Не удалось найти пользователя {user_id} для обновления.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка обновления статуса для {user_id}: {e}")

# --- Секция работы с локальной базой SQLite ---
def get_db_connection():
    # Создаем директорию для базы данных если её нет
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует/обновляет структуру базы данных."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # --- Таблица Пользователей (users) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT, first_name TEXT,
                status TEXT DEFAULT 'registered',
                source TEXT,
                referrer_id INTEGER,
                brought_by_staff_id INTEGER,
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeem_date TIMESTAMP,
                last_check_date TIMESTAMP
            )""")
        
        # Проверка и добавление колонки brought_by_staff_id для совместимости
        try:
            cur.execute("SELECT brought_by_staff_id FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN brought_by_staff_id INTEGER")

        # Проверка и добавление колонки phone_number для контактов
        try:
            cur.execute("SELECT phone_number FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")

        # Проверка и добавление колонок для реферальной системы наград
        try:
            cur.execute("SELECT referrer_rewarded FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN referrer_rewarded INTEGER DEFAULT 0")

        try:
            cur.execute("SELECT referrer_rewarded_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN referrer_rewarded_date TEXT")
            logging.info("База данных обновлена: добавлена колонка referrer_rewarded_date")

        # Проверка и добавление колонки contact_shared_date для даты предоставления контакта
        try:
            cur.execute("SELECT contact_shared_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN contact_shared_date TIMESTAMP")
            logging.info("База данных обновлена: добавлена колонка contact_shared_date")

        # Проверка и добавление колонки real_name для настоящего имени
        try:
            cur.execute("SELECT real_name FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN real_name TEXT")
            logging.info("База данных обновлена: добавлена колонка real_name")

        # Проверка и добавление колонки birth_date для даты рождения
        try:
            cur.execute("SELECT birth_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN birth_date DATE")
            logging.info("База данных обновлена: добавлена колонка birth_date")

        # Проверка и добавление колонки profile_completed для отслеживания завершенности профиля
        try:
            cur.execute("SELECT profile_completed FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN profile_completed BOOLEAN DEFAULT 0")
            logging.info("База данных обновлена: добавлена колонка profile_completed")

        # Проверка и добавление колонки ai_concept для концепции AI-ассистента
        try:
            cur.execute("SELECT ai_concept FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN ai_concept TEXT DEFAULT 'evgenich'")
            logging.info("База данных обновлена: добавлена колонка ai_concept")

        # Проверка и добавление колонок для системы рассылок
        try:
            cur.execute("SELECT blocked FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0")
            logging.info("База данных обновлена: добавлена колонка blocked")

        try:
            cur.execute("SELECT block_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE users ADD COLUMN block_date TEXT")
            logging.info("База данных обновлена: добавлена колонка block_date")

        # --- НОВАЯ ТАБЛИЦА: Персонал (staff) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT,
                short_name TEXT,
                position TEXT,
                unique_code TEXT UNIQUE,
                status TEXT DEFAULT 'active'
            )""")

        # Остальные таблицы
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT,
                text TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                rating INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # --- НОВАЯ ТАБЛИЦА: Отложенные задачи (delayed_tasks) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS delayed_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_type TEXT,
                scheduled_time TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # --- НОВАЯ ТАБЛИЦА: Данные iiko (iiko_data) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS iiko_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE,
                nastoika_count INTEGER,
                reported_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # --- НОВЫЕ ТАБЛИЦЫ: Система рассылок ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS newsletters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                media_type TEXT,
                media_file_id TEXT,
                status TEXT DEFAULT 'draft',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scheduled_time TIMESTAMP,
                sent_at TIMESTAMP,
                target_count INTEGER DEFAULT 0,
                delivered_count INTEGER DEFAULT 0,
                read_count INTEGER DEFAULT 0
            )""")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS newsletter_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_id INTEGER,
                text TEXT NOT NULL,
                url TEXT NOT NULL,
                utm_campaign TEXT,
                utm_source TEXT DEFAULT 'telegram_bot',
                utm_medium TEXT DEFAULT 'newsletter',
                utm_content TEXT,
                position INTEGER DEFAULT 0,
                FOREIGN KEY (newsletter_id) REFERENCES newsletters (id)
            )""")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS newsletter_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_id INTEGER,
                user_id INTEGER,
                delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                FOREIGN KEY (newsletter_id) REFERENCES newsletters (id)
            )""")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS newsletter_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_id INTEGER,
                button_id INTEGER,
                user_id INTEGER,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (newsletter_id) REFERENCES newsletters (id),
                FOREIGN KEY (button_id) REFERENCES newsletter_buttons (id)
            )""")
            
        conn.commit()
        conn.close()
        logging.info("База данных SQLite успешно инициализирована/обновлена.")
    except Exception as e:
        logging.critical(f"Не удалось инициализировать базу данных SQLite: {e}")

# --- Функции для работы с Пользователями (users) ---

def add_new_user(user_id: int, username: str, first_name: str, source: str, referrer_id: Optional[int] = None, brought_by_staff_id: Optional[int] = None):
    """Добавляет нового пользователя, возможно с привязкой к сотруднику."""
    moscow_tz = pytz.timezone('Europe/Moscow')
    signup_time = datetime.datetime.now(moscow_tz)
    
    if USE_POSTGRES:
        # Добавление пользователя через PostgreSQL
        try:
            success = pg_client.add_new_user(
                user_id=user_id,
                username=username or "N/A",
                first_name=first_name,
                source=source,
                referrer_id=referrer_id,
                brought_by_staff_id=brought_by_staff_id
            )
            if not success:
                logging.warning(f"PostgreSQL | Пользователь {user_id} уже существует или произошла ошибка")
                return
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка добавления пользователя {user_id}: {e}")
            return
    else:
        # Добавление пользователя через SQLite
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name, source, referrer_id, brought_by_staff_id, signup_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username or "N/A", first_name, source, referrer_id, brought_by_staff_id, signup_time)
            )
            conn.commit()
            conn.close()
            logging.info(f"SQLite | Пользователь {user_id} добавлен. Источник: {source}, Сотрудник: {brought_by_staff_id}")
        except Exception as e:
            logging.error(f"SQLite | Ошибка добавления пользователя {user_id}: {e}")
            return
    # Логика для Google Sheets
    logging.info(f"📝 Подготовка данных пользователя {user_id} для Google Sheets...")
    row_data = [
        signup_time.strftime('%Y-%m-%d %H:%M:%S'), user_id, first_name,
        username or "N/A", "", "", "",  # phone_number, real_name, birth_date пока пустые
        _translate_status_to_russian('registered'), source, 
        referrer_id if referrer_id else "", ""  # реферер ID и дата погашения
    ]
    logging.info(f"📝 GOOGLE_SHEETS_ENABLED={GOOGLE_SHEETS_ENABLED}, GOOGLE_SHEET_KEY={bool(GOOGLE_SHEET_KEY)}, GOOGLE_CREDENTIALS_JSON={bool(GOOGLE_CREDENTIALS_JSON)}")
    if GOOGLE_SHEETS_ENABLED:
        logging.info(f"✅ Запускаю фоновую задачу добавления пользователя {user_id} в Google Sheets...")
        threading.Thread(target=_add_user_to_sheets_in_background, args=(row_data,)).start()
    else:
        logging.warning(f"⚠️  Google Sheets отключен для пользователя {user_id}!")

def update_status(user_id: int, new_status: str) -> bool:
    redeem_time = datetime.datetime.now(pytz.utc) if new_status == 'redeemed' else None
    updated = False
    
    if USE_POSTGRES:
        # Обновление статуса через PostgreSQL
        try:
            updated = pg_client.update_status(user_id, new_status)
            
            if updated and new_status == 'redeemed':
                # Дополнительно сохраняем дату погашения и планируем сообщение
                # Эти данные должны быть реализованы в PostgreSQL клиенте
                # ToDo: Реализовать сохранение даты погашения в PostgreSQL
                schedule_delayed_message(user_id, 'engagement_after_redeem', 10)
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка обновления статуса для {user_id}: {e}")
            return False
    else:
        # Обновление статуса через SQLite
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            if redeem_time:
                # При погашении сразу ставим дату проверки, чтобы аудитор его проверил
                cur.execute("UPDATE users SET status = ?, redeem_date = ?, last_check_date = ? WHERE user_id = ?", (new_status, redeem_time, datetime.datetime.now(pytz.utc), user_id))
            else:
                cur.execute("UPDATE users SET status = ? WHERE user_id = ?", (new_status, user_id))
            updated = cur.rowcount > 0
            conn.commit()
            conn.close()
            if updated:
                logging.info(f"SQLite | Статус пользователя {user_id} обновлен на {new_status}.")
                # Планируем отложенное сообщение при погашении купона
                if new_status == 'redeemed':
                    schedule_delayed_message(user_id, 'engagement_after_redeem', 10)
        except Exception as e:
            logging.error(f"SQLite | Ошибка обновления статуса для {user_id}: {e}")
            return False
    if updated and GOOGLE_SHEETS_ENABLED:
        threading.Thread(target=_update_status_in_sheets_in_background, args=(user_id, new_status, redeem_time)).start()
    return updated

def update_user_contact(user_id: int, phone_number: str) -> bool:
    """Обновляет контактную информацию пользователя."""
    contact_time = datetime.datetime.now(pytz.utc)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Сначала проверяем, существует ли пользователь
        cur.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        user_exists = cur.fetchone()[0] > 0
        
        if not user_exists:
            # Если пользователь не существует, создаем его с базовой информацией
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, source, signup_date, phone_number, contact_shared_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, "N/A", "N/A", "contact_direct", contact_time, phone_number, contact_time)
            )
            logging.info(f"SQLite | Создан новый пользователь {user_id} с контактом: {phone_number}")
        else:
            # Если пользователь существует, обновляем его контакт
            cur.execute(
                "UPDATE users SET phone_number = ?, contact_shared_date = ? WHERE user_id = ?",
                (phone_number, contact_time, user_id)
            )
            logging.info(f"SQLite | Контакт пользователя {user_id} обновлен: {phone_number}")
        
        conn.commit()
        conn.close()
        
        # Обновляем в Google Sheets в фоновом режиме
        if GOOGLE_SHEETS_ENABLED:
            threading.Thread(target=_update_contact_in_sheets_in_background, args=(user_id, phone_number, contact_time)).start()
        
        return True
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления контакта для {user_id}: {e}")
        return False

def get_user_phone(user_id: int) -> str:
    """Получает номер телефона пользователя из базы данных."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
        return None
    except Exception as e:
        logging.error(f"SQLite | Ошибка получения телефона для {user_id}: {e}")
        return None

def update_user_name(user_id: int, real_name: str) -> bool:
    """Обновляет настоящее имя пользователя."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Сначала проверяем, существует ли пользователь
        cur.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        user_exists = cur.fetchone()[0] > 0
        
        if not user_exists:
            # Если пользователь не существует, создаем его с базовой информацией
            current_time = datetime.datetime.now(pytz.utc)
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, source, signup_date, real_name) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, "N/A", real_name, "name_direct", current_time, real_name)
            )
            logging.info(f"SQLite | Создан новый пользователь {user_id} с именем: {real_name}")
        else:
            # Если пользователь существует, обновляем его имя
            cur.execute(
                "UPDATE users SET real_name = ? WHERE user_id = ?",
                (real_name, user_id)
            )
            logging.info(f"SQLite | Имя пользователя {user_id} обновлено: {real_name}")
        
        conn.commit()
        conn.close()
        
        # Обновляем в Google Sheets в фоновом режиме
        if GOOGLE_SHEETS_ENABLED:
            threading.Thread(target=_update_name_in_sheets_in_background, args=(user_id, real_name)).start()
        
        return True
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления имени для {user_id}: {e}")
        return False

def update_user_birth_date(user_id: int, birth_date: str) -> bool:
    """Обновляет дату рождения пользователя."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Сначала проверяем, существует ли пользователь
        cur.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        user_exists = cur.fetchone()[0] > 0
        
        if not user_exists:
            # Если пользователь не существует, создаем его с базовой информацией
            current_time = datetime.datetime.now(pytz.utc)
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, source, signup_date, birth_date, profile_completed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, "N/A", "N/A", "birth_direct", current_time, birth_date, 1)
            )
            logging.info(f"SQLite | Создан новый пользователь {user_id} с датой рождения: {birth_date}")
        else:
            # Если пользователь существует, обновляем его дату рождения
            cur.execute(
                "UPDATE users SET birth_date = ?, profile_completed = 1 WHERE user_id = ?",
                (birth_date, user_id)
            )
            logging.info(f"SQLite | Дата рождения пользователя {user_id} обновлена: {birth_date}")
        
        conn.commit()
        conn.close()
        
        # Обновляем в Google Sheets в фоновом режиме
        if GOOGLE_SHEETS_ENABLED:
            threading.Thread(target=_update_birth_date_in_sheets_in_background, args=(user_id, birth_date)).start()
        
        return True
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления даты рождения для {user_id}: {e}")
        return False

def update_user_source(user_id: int, source: str) -> bool:
    """Обновляет источник пользователя (при переходе по новой ссылке)."""
    # Сначала пробуем PostgreSQL
    if USE_POSTGRES and pg_client:
        try:
            success = pg_client.update_user_source(user_id, source)
            if success:
                return True
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка обновления источника: {e}")
    
    # Fallback на SQLite
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE users SET source = ? WHERE user_id = ?",
            (source, user_id)
        )
        
        conn.commit()
        conn.close()
        logging.info(f"SQLite | Источник пользователя {user_id} обновлен: {source}")
        return True
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления источника для {user_id}: {e}")
        return False

def find_user_by_id(user_id: int) -> Optional[dict]:
    """Находит пользователя по ID. Возвращает dict для совместимости."""
    # Сначала пробуем PostgreSQL
    if USE_POSTGRES and pg_client:
        try:
            user = pg_client.get_user_by_id(user_id)
            if user:
                return user
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка поиска пользователя {user_id}: {e}")
    
    # Fallback на SQLite
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()
        conn.close()
        if user:
            # Конвертируем sqlite3.Row в dict для совместимости
            return dict(user)
        return None
    except Exception as e:
        logging.error(f"SQLite | Ошибка поиска пользователя {user_id}: {e}")
        return None

def find_user_by_id_or_username(identifier: str) -> Optional[sqlite3.Row]:
    """Находит пользователя по ID или @username."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        clean_identifier = identifier.lstrip('@')
        if clean_identifier.isdigit():
            user_id = int(clean_identifier)
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        else:
            cur.execute("SELECT * FROM users WHERE username = ?", (clean_identifier,))
        user = cur.fetchone()
        conn.close()
        return user
    except Exception as e:
        logging.error(f"SQLite | Ошибка поиска пользователя по идентификатору '{identifier}': {e}")
        return None

def get_reward_status(user_id: int) -> str:
    user = find_user_by_id(user_id)
    return user['status'] if user else 'not_found'

def delete_user(user_id: int) -> Tuple[bool, str]:
    # Сначала пробуем PostgreSQL
    if USE_POSTGRES and pg_client:
        try:
            success, msg = pg_client.delete_user(user_id)
            if success:
                return success, msg
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка удаления пользователя: {e}")
    
    # Fallback на SQLite
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        if deleted:
            msg = f"Пользователь {user_id} успешно удален из SQLite."
            logging.info(msg)
            return True, msg
        else:
            msg = f"Пользователь {user_id} не найден в SQLite для удаления."
            return False, msg
    except Exception as e:
        error_msg = f"Ошибка удаления пользователя {user_id} из SQLite: {e}"
        logging.error(error_msg)
        return False, error_msg

def get_referrer_id_from_user(user_id: int) -> Optional[int]:
    user = find_user_by_id(user_id)
    if user and user['referrer_id']:
        return int(user['referrer_id'])
    return None

def get_user_concept(user_id: int) -> str:
    """
    Получает AI концепцию пользователя из базы данных.
    
    Args:
        user_id (int): ID пользователя Telegram
        
    Returns:
        str: Концепция AI ассистента ('evgenich' по умолчанию)
    """
    try:
        if USE_POSTGRES:
            user = pg_client.get_user_by_id(user_id)
            if user and 'ai_concept' in user:
                return user['ai_concept'] or 'evgenich'
        
        # Fallback на SQLite
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT ai_concept FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        
        return 'evgenich'  # Значение по умолчанию
        
    except Exception as e:
        logging.error(f"Ошибка при получении концепции пользователя {user_id}: {e}")
        return 'evgenich'

def update_user_concept(user_id: int, concept: str) -> bool:
    """
    Обновляет AI концепцию пользователя в базе данных.
    
    Args:
        user_id (int): ID пользователя Telegram
        concept (str): Новая концепция AI ассистента
        
    Returns:
        bool: True если обновление успешно, False в противном случае
    """
    try:
        if USE_POSTGRES:
            success = pg_client.update_user_concept(user_id, concept)
            if not success:
                logging.warning(f"PostgreSQL | Не удалось обновить концепцию для пользователя {user_id}")
        
        # Обновляем в SQLite
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET ai_concept = ? WHERE user_id = ?", (concept, user_id))
        conn.commit()
        conn.close()
        
        logging.info(f"Концепция пользователя {user_id} обновлена на {concept}")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при обновлении концепции пользователя {user_id}: {e}")
        return False

def get_redeemed_users_for_audit() -> List[sqlite3.Row]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE status = 'redeemed'")
        users = cur.fetchall()
        conn.close()
        return users
    except Exception as e:
        logging.error(f"Аудитор | Ошибка получения пользователей для проверки: {e}")
        return []

def mark_user_as_left(user_id: int):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.datetime.now(pytz.utc)
        cur.execute("UPDATE users SET status = ?, last_check_date = ? WHERE user_id = ?", ('redeemed_and_left', now, user_id))
        conn.commit()
        conn.close()
        logging.info(f"Аудитор | Пользователь {user_id} помечен как отписавшийся.")
    except Exception as e:
        logging.error(f"Аудитор | Ошибка при обновлении статуса пользователя {user_id}: {e}")

def get_daily_churn_data(start_time: datetime, end_time: datetime) -> Tuple[int, int]:
    try:
        # Используем PostgreSQL если включен
        if USE_POSTGRES and pg_client:
            return pg_client.get_daily_churn_data(start_time, end_time)
        
        # Иначе используем SQLite
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Конвертируем datetime в строку формата, подходящего для текущей БД
        start_str = _format_dt_for_db(start_time)
        end_str = _format_dt_for_db(end_time)
        
        cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ? AND status IN ('redeemed', 'redeemed_and_left')", (start_str, end_str))
        redeemed_total = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ? AND status = 'redeemed_and_left'",
            (start_str, end_str)
        )
        left_count = cur.fetchone()[0]
        conn.close()
        return redeemed_total, left_count
    except Exception as e:
        logging.error(f"Отчет | Ошибка получения данных о дневном оттоке: {e}")
        return 0, 0

def get_full_churn_analysis() -> Tuple[int, Dict[str, int]]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT redeem_date, last_check_date FROM users WHERE status = 'redeemed_and_left'")
        left_users = cur.fetchall()
        conn.close()
        total_left = len(left_users)
        lifetime_distribution = {"В течение суток": 0, "1-3 дня": 0, "4-7 дней": 0, "Более недели": 0}
        for user in left_users:
            if not user['redeem_date'] or not user['last_check_date']: continue
            redeem_dt = datetime.datetime.fromisoformat(user['redeem_date'])
            check_dt = datetime.datetime.fromisoformat(user['last_check_date'])
            lifetime_days = (check_dt - redeem_dt).days
            if lifetime_days <= 1: lifetime_distribution["В течение суток"] += 1
            elif 1 < lifetime_days <= 3: lifetime_distribution["1-3 дня"] += 1
            elif 3 < lifetime_days <= 7: lifetime_distribution["4-7 дней"] += 1
            else: lifetime_distribution["Более недели"] += 1
        return total_left, lifetime_distribution
    except Exception as e:
        logging.error(f"Отчет | Ошибка получения полной аналитики по оттоку: {e}")
        return 0, {}

def get_report_data_for_period(start_time: datetime, end_time: datetime) -> tuple:
    try:
        # Используем PostgreSQL если включен
        if USE_POSTGRES and pg_client:
            return pg_client.get_report_data_for_period(start_time, end_time)
        
        # Иначе используем SQLite
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Конвертируем datetime в строку формата, подходящего для текущей БД
        start_str = _format_dt_for_db(start_time)
        end_str = _format_dt_for_db(end_time)
        
        cur.execute("SELECT COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? AND status IN ('issued', 'redeemed', 'redeemed_and_left')", (start_str, end_str))
        issued_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ?", (start_str, end_str))
        redeemed_count = cur.fetchone()[0]
        cur.execute("SELECT source, COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? GROUP BY source", (start_str, end_str))
        all_sources = {row['source']: row['COUNT(*)'] for row in cur.fetchall()}
        
        # Фильтруем источники: все обычные источники
        sources = {k: v for k, v in all_sources.items() if k != "staff"}
        
        # Подсчитываем переходы от сотрудников отдельно
        staff_count = all_sources.get("staff", 0)
        if staff_count > 0:
            sources["staff"] = staff_count
        total_redeem_time_seconds = 0
        if redeemed_count > 0:
            cur.execute("SELECT SUM(strftime('%s', redeem_date) - strftime('%s', signup_date)) FROM users WHERE redeem_date BETWEEN ? AND ? AND status IN ('redeemed', 'redeemed_and_left')", (start_str, end_str))
            total_redeem_time_seconds_row = cur.fetchone()[0]
            total_redeem_time_seconds = total_redeem_time_seconds_row or 0
        conn.close()
        return issued_count, redeemed_count, [], sources, total_redeem_time_seconds
    except Exception as e:
        logging.error(f"Ошибка сбора данных для отчета: {e}")
        return 0, 0, [], {}, 0

def log_conversation_turn(user_id: int, role: str, text: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversation_history (user_id, role, text) VALUES (?, ?, ?)",
            (user_id, role, text)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка логирования диалога для {user_id}: {e}")

def get_conversation_history(user_id: int, limit: int = 10) -> List[Dict[str, str]]:
    history = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT role, text FROM conversation_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cur.fetchall()
        conn.close()
        for row in reversed(rows):
            history.append({"role": row['role'], "content": row['text']})
        return history
    except Exception as e:
        logging.error(f"Ошибка получения истории диалога для {user_id}: {e}")
        return history

def log_ai_feedback(user_id: int, query: str, response: str, rating: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feedback (user_id, rating) VALUES (?, ?)",
            (user_id, int(rating))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка логирования обратной связи для {user_id}: {e}")
        
def get_top_referrers_for_month(limit: int = 5) -> List[Tuple[str, int]]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT referrer_id, COUNT(*) as ref_count
            FROM users
            WHERE status IN ('redeemed', 'redeemed_and_left')
              AND referrer_id IS NOT NULL
              AND strftime('%Y-%m', redeem_date) = strftime('%Y-%m', 'now')
            GROUP BY referrer_id
            ORDER BY ref_count DESC
            LIMIT ?
        """, (limit,))
        top_referrers_ids = cur.fetchall()
        if not top_referrers_ids:
            conn.close()
            return []
        top_list = []
        for row in top_referrers_ids:
            cur.execute("SELECT first_name, username FROM users WHERE user_id = ?", (row['referrer_id'],))
            user_info = cur.fetchone()
            name = f"@{user_info['username']}" if user_info and user_info['username'] != "N/A" else (user_info['first_name'] if user_info else f"ID {row['referrer_id']}")
            top_list.append((name, row['ref_count']))
        conn.close()
        return top_list
    except Exception as e:
        logging.error(f"Ошибка получения топа рефереров из SQLite: {e}")
        return []

def get_daily_updates() -> dict:
    return {'special': 'нет', 'stop-list': 'ничего'}

# --- Функции для реферальной системы наград ---

def check_referral_reward_eligibility(referrer_id: int, referred_id: int):
    """
    Проверяет, можно ли выдать награду за реферала.
    Условия:
    1. Реферал должен быть зарегистрирован более 48 часов назад
    2. Реферал должен получить настойку (redeem_date не NULL)
    3. Награда еще не была выдана за этого реферала
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.check_referral_reward_eligibility(referrer_id, referred_id)
        
        # SQLite версия
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Получаем данные реферала
        cur.execute("""
            SELECT signup_date, redeem_date, referrer_rewarded
            FROM users 
            WHERE user_id = ? AND referrer_id = ?
        """, (referred_id, referrer_id))
        
        result = cur.fetchone()
        if not result:
            conn.close()
            return False, "Реферал не найден"
        
        signup_date_str, redeem_date, referrer_rewarded = result
        
        # Проверяем, была ли уже выдана награда
        if referrer_rewarded:
            conn.close()
            return False, "Награда уже была выдана"
        
        # Проверяем, получил ли реферал настойку
        if not redeem_date:
            conn.close()
            return False, "Реферал еще не получил настойку"
        
        # Проверяем, прошло ли 48 часов с момента регистрации
        if signup_date_str:
            signup_date = datetime.datetime.fromisoformat(signup_date_str.replace('Z', '+00:00'))
            current_time = datetime.datetime.now(pytz.utc)
            hours_passed = (current_time - signup_date).total_seconds() / 3600
            
            if hours_passed < 48:
                hours_left = 48 - hours_passed
                conn.close()
                return False, f"До получения награды осталось {int(hours_left)} часов"
        
        conn.close()
        return True, "Можно выдать награду"
        
    except Exception as e:
        logging.error(f"Ошибка проверки права на награду: {e}")
        return False, "Ошибка проверки"

def mark_referral_rewarded(referrer_id: int, referred_id: int):
    """
    Отмечает, что награда за реферала была выдана
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.mark_referral_rewarded(referrer_id, referred_id)
        
        # SQLite версия
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE users 
            SET referrer_rewarded = 1,
                referrer_rewarded_date = ?
            WHERE user_id = ? AND referrer_id = ?
        """, (datetime.datetime.now(pytz.utc).isoformat(), referred_id, referrer_id))
        
        conn.commit()
        success = cur.rowcount > 0
        conn.close()
        
        return success
        
    except Exception as e:
        logging.error(f"Ошибка отметки награды: {e}")
        return False

def get_referral_stats(user_id: int):
    """
    Получает статистику по рефералам пользователя
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.get_referral_stats(user_id)
        
        # SQLite версия
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Общее количество рефералов
        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        total_referrals = cur.fetchone()[0]
        
        # Количество рефералов, получивших настойку
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE referrer_id = ? AND redeem_date IS NOT NULL
        """, (user_id,))
        redeemed_referrals = cur.fetchone()[0]
        
        # Количество полученных наград
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE referrer_id = ? AND referrer_rewarded = 1
        """, (user_id,))
        rewards_received = cur.fetchone()[0]
        
        # Рефералы, ожидающие 48 часов
        cur.execute("""
            SELECT user_id, username, first_name, signup_date, redeem_date
            FROM users 
            WHERE referrer_id = ? 
            AND redeem_date IS NOT NULL 
            AND referrer_rewarded = 0
            ORDER BY signup_date DESC
        """, (user_id,))
        
        pending_rewards = []
        for row in cur.fetchall():
            ref_id, username, first_name, signup_date_str, redeem_date = row
            
            if signup_date_str:
                signup_date = datetime.datetime.fromisoformat(signup_date_str.replace('Z', '+00:00'))
                hours_passed = (datetime.datetime.now(pytz.utc) - signup_date).total_seconds() / 3600
                
                pending_rewards.append({
                    'user_id': ref_id,
                    'username': username,
                    'first_name': first_name,
                    'hours_passed': int(hours_passed),
                    'hours_left': max(0, 48 - int(hours_passed)),
                    'can_claim': hours_passed >= 48
                })
        
        conn.close()
        
        return {
            'total': total_referrals,
            'redeemed': redeemed_referrals,
            'rewarded': rewards_received,
            'pending': pending_rewards
        }
        
    except Exception as e:
        logging.error(f"Ошибка получения статистики рефералов: {e}")
        return None

def get_users_with_pending_rewards():
    """
    Возвращает список user_id пользователей, у которых есть рефералы,
    готовые к получению награды
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.get_users_with_pending_rewards()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Находим всех пользователей с рефералами, которые:
        # 1. Получили настойку
        # 2. Зарегистрированы более 48 часов назад
        # 3. Еще не получили награду
        cur.execute("""
            SELECT DISTINCT referrer_id
            FROM users
            WHERE referrer_id IS NOT NULL
            AND redeem_date IS NOT NULL
            AND referrer_rewarded = 0
            AND julianday('now') - julianday(signup_date) > 2
        """)
        
        users = [row[0] for row in cur.fetchall()]
        conn.close()
        
        return users
        
    except Exception as e:
        logging.error(f"Ошибка получения пользователей с наградами: {e}")
        return []

def get_recently_redeemed_referrals(hours: int = 2):
    """
    Возвращает список рефералов, которые получили настойку в последние N часов
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.get_recently_redeemed_referrals(hours)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Находим рефералов, получивших настойку в последние N часов
        hours_ago = datetime.datetime.now(pytz.utc) - datetime.timedelta(hours=hours)
        
        cur.execute("""
            SELECT user_id, username, first_name, referrer_id, redeem_date
            FROM users
            WHERE referrer_id IS NOT NULL
            AND redeem_date IS NOT NULL
            AND datetime(redeem_date) >= datetime(?)
            AND referrer_rewarded = 0
            ORDER BY redeem_date DESC
        """, (hours_ago.isoformat(),))
        
        recent_referrals = []
        for row in cur.fetchall():
            user_id, username, first_name, referrer_id, redeem_date = row
            recent_referrals.append({
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'referrer_id': referrer_id,
                'redeem_date': redeem_date
            })
        
        conn.close()
        return recent_referrals
        
    except Exception as e:
        logging.error(f"Ошибка получения недавних активаций рефералов: {e}")
        return []

# --- Функции для работы с отложенными задачами (delayed_tasks) ---

def schedule_delayed_message(user_id: int, task_type: str, delay_minutes: int = 10):
    """Планирует отложенное сообщение для пользователя."""
    try:
        scheduled_time = datetime.datetime.now(pytz.utc) + datetime.timedelta(minutes=delay_minutes)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO delayed_tasks (user_id, task_type, scheduled_time) VALUES (?, ?, ?)",
            (user_id, task_type, scheduled_time)
        )
        conn.commit()
        conn.close()
        logging.info(f"Отложенная задача '{task_type}' запланирована для пользователя {user_id} на {scheduled_time}")
    except Exception as e:
        logging.error(f"Ошибка планирования отложенной задачи для {user_id}: {e}")

def get_pending_delayed_tasks() -> List[sqlite3.Row]:
    """Получает все отложенные задачи, готовые к выполнению."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.datetime.now(pytz.utc)
        cur.execute(
            "SELECT * FROM delayed_tasks WHERE status = 'pending' AND scheduled_time <= ?",
            (now,)
        )
        tasks = cur.fetchall()
        conn.close()
        return tasks
    except Exception as e:
        logging.error(f"Ошибка получения отложенных задач: {e}")
        return []

def mark_delayed_task_completed(task_id: int):
    """Помечает отложенную задачу как выполненную."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE delayed_tasks SET status = 'completed' WHERE id = ?",
            (task_id,)
        )
        conn.commit()
        conn.close()
        logging.info(f"Отложенная задача {task_id} помечена как выполненная")
    except Exception as e:
        logging.error(f"Ошибка обновления статуса задачи {task_id}: {e}")

def cleanup_old_delayed_tasks(days_old: int = 7):
    """Удаляет старые выполненные задачи."""
    try:
        cutoff_date = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=days_old)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM delayed_tasks WHERE status = 'completed' AND created_at < ?",
            (cutoff_date,)
        )
        deleted_count = cur.rowcount
        conn.commit()
        conn.close()
        if deleted_count > 0:
            logging.info(f"Удалено {deleted_count} старых отложенных задач")
    except Exception as e:
        logging.error(f"Ошибка очистки старых задач: {e}")

# --- Функции для работы с данными iiko ---

def save_iiko_nastoika_count(report_date: datetime.date, nastoika_count: int, reported_by_user_id: int) -> bool:
    """Сохраняет количество настоек из iiko за определенную дату."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Используем INSERT OR REPLACE для обновления данных за ту же дату
        cur.execute(
            "INSERT OR REPLACE INTO iiko_data (report_date, nastoika_count, reported_by_user_id) VALUES (?, ?, ?)",
            (report_date, nastoika_count, reported_by_user_id)
        )
        conn.commit()
        conn.close()
        logging.info(f"Данные iiko сохранены: {report_date} - {nastoika_count} настоек (от пользователя {reported_by_user_id})")
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения данных iiko: {e}")
        return False

def get_iiko_nastoika_count_for_date(report_date: datetime.date) -> Optional[int]:
    """Получает количество настоек из iiko за определенную дату."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT nastoika_count FROM iiko_data WHERE report_date = ?",
            (report_date,)
        )
        result = cur.fetchone()
        conn.close()
        return result['nastoika_count'] if result else None
    except Exception as e:
        logging.error(f"Ошибка получения данных iiko за {report_date}: {e}")
        return None

def is_waiting_for_iiko_data(report_date: datetime.date) -> bool:
    """Проверяет, ожидаются ли данные iiko за определенную дату."""
    # Данные ожидаются, если они еще не внесены
    return get_iiko_nastoika_count_for_date(report_date) is None

# --- Функции для работы с рассылками ---

def get_newsletter_audience_count() -> int:
    """Возвращает количество активных пользователей для рассылки."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Считаем всех зарегистрированных пользователей (исключаем только полностью отписавшихся)
        cur.execute("SELECT COUNT(*) FROM users WHERE status != 'redeemed_and_left'")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logging.error(f"Ошибка подсчета аудитории рассылки: {e}")
        return 0

def create_newsletter(title: str, content: str, created_by: int, media_type: str = None, media_file_id: str = None) -> int:
    """Создает новую рассылку и возвращает ее ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO newsletters (title, content, media_type, media_file_id, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (title, content, media_type, media_file_id, created_by))
        newsletter_id = cur.lastrowid
        conn.commit()
        conn.close()
        logging.info(f"Создана рассылка '{title}' с ID {newsletter_id}")
        return newsletter_id
    except Exception as e:
        logging.error(f"Ошибка создания рассылки: {e}")
        return 0

def add_newsletter_button(newsletter_id: int, text: str, url: str, position: int = 0) -> int:
    """Добавляет кнопку к рассылке с UTM-метками."""
    try:
        utm_campaign = f"newsletter_{newsletter_id}"
        utm_content = f"button_{newsletter_id}_{position}"
        
        # Добавляем UTM-параметры к URL
        separator = "&" if "?" in url else "?"
        tracked_url = f"{url}{separator}utm_source=telegram_bot&utm_medium=newsletter&utm_campaign={utm_campaign}&utm_content={utm_content}"
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO newsletter_buttons (newsletter_id, text, url, utm_campaign, utm_content, position)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (newsletter_id, text, tracked_url, utm_campaign, utm_content, position))
        button_id = cur.lastrowid
        conn.commit()
        conn.close()
        logging.info(f"Добавлена кнопка '{text}' к рассылке {newsletter_id}")
        return button_id
    except Exception as e:
        logging.error(f"Ошибка добавления кнопки к рассылке: {e}")
        return 0

def get_newsletter_by_id(newsletter_id: int) -> Optional[sqlite3.Row]:
    """Получает рассылку по ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM newsletters WHERE id = ?", (newsletter_id,))
        newsletter = cur.fetchone()
        conn.close()
        return newsletter
    except Exception as e:
        logging.error(f"Ошибка получения рассылки {newsletter_id}: {e}")
        return None

def get_newsletter_buttons(newsletter_id: int) -> List[sqlite3.Row]:
    """Получает кнопки рассылки."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM newsletter_buttons WHERE newsletter_id = ? ORDER BY position", (newsletter_id,))
        buttons = cur.fetchall()
        conn.close()
        return buttons
    except Exception as e:
        logging.error(f"Ошибка получения кнопок рассылки {newsletter_id}: {e}")
        return []

def get_user_newsletters(created_by: int = None, limit: int = 10) -> List[sqlite3.Row]:
    """Получает список рассылок пользователя."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if created_by:
            cur.execute("SELECT * FROM newsletters WHERE created_by = ? ORDER BY created_at DESC LIMIT ?", (created_by, limit))
        else:
            cur.execute("SELECT * FROM newsletters ORDER BY created_at DESC LIMIT ?", (limit,))
        newsletters = cur.fetchall()
        conn.close()
        return newsletters
    except Exception as e:
        logging.error(f"Ошибка получения списка рассылок: {e}")
        return []

def schedule_newsletter(newsletter_id: int, scheduled_time: datetime.datetime) -> bool:
    """Планирует рассылку на определенное время."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE newsletters 
            SET status = 'scheduled', scheduled_time = ? 
            WHERE id = ?
        """, (scheduled_time, newsletter_id))
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        if updated:
            logging.info(f"Рассылка {newsletter_id} запланирована на {scheduled_time}")
        return updated
    except Exception as e:
        logging.error(f"Ошибка планирования рассылки {newsletter_id}: {e}")
        return False

def mark_newsletter_sent(newsletter_id: int, target_count: int, delivered_count: int) -> bool:
    """Отмечает рассылку как отправленную."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE newsletters 
            SET status = 'sent', sent_at = ?, target_count = ?, delivered_count = ? 
            WHERE id = ?
        """, (datetime.datetime.now(pytz.utc), target_count, delivered_count, newsletter_id))
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        if updated:
            logging.info(f"Рассылка {newsletter_id} отмечена как отправленная")
        return updated
    except Exception as e:
        logging.error(f"Ошибка обновления статуса рассылки {newsletter_id}: {e}")
        return False

def track_newsletter_delivery(newsletter_id: int, user_id: int) -> bool:
    """Отслеживает доставку рассылки пользователю."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO newsletter_stats (newsletter_id, user_id)
            VALUES (?, ?)
        """, (newsletter_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка отслеживания доставки рассылки {newsletter_id} пользователю {user_id}: {e}")
        return False

def track_newsletter_click(newsletter_id: int, button_id: int, user_id: int) -> bool:
    """Отслеживает клик по кнопке в рассылке."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO newsletter_clicks (newsletter_id, button_id, user_id)
            VALUES (?, ?, ?)
        """, (newsletter_id, button_id, user_id))
        conn.commit()
        conn.close()
        logging.info(f"Зафиксирован клик по кнопке {button_id} в рассылке {newsletter_id} от пользователя {user_id}")
        return True
    except Exception as e:
        logging.error(f"Ошибка отслеживания клика: {e}")
        return False

def get_newsletter_analytics(newsletter_id: int) -> Dict[str, Any]:
    """Получает аналитику по рассылке."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Общая статистика
        cur.execute("SELECT target_count, delivered_count FROM newsletters WHERE id = ?", (newsletter_id,))
        newsletter_stats = cur.fetchone()
        
        # Статистика кликов по кнопкам
        cur.execute("""
            SELECT b.text, b.utm_content, COUNT(c.id) as clicks
            FROM newsletter_buttons b
            LEFT JOIN newsletter_clicks c ON b.id = c.button_id
            WHERE b.newsletter_id = ?
            GROUP BY b.id, b.text, b.utm_content
        """, (newsletter_id,))
        button_stats = cur.fetchall()
        
        # Общее количество кликов
        cur.execute("SELECT COUNT(*) FROM newsletter_clicks WHERE newsletter_id = ?", (newsletter_id,))
        total_clicks = cur.fetchone()[0]
        
        conn.close()
        
        return {
            'target_count': newsletter_stats['target_count'] if newsletter_stats else 0,
            'delivered_count': newsletter_stats['delivered_count'] if newsletter_stats else 0,
            'total_clicks': total_clicks,
            'button_stats': [dict(row) for row in button_stats]
        }
    except Exception as e:
        logging.error(f"Ошибка получения аналитики рассылки {newsletter_id}: {e}")
        return {'target_count': 0, 'delivered_count': 0, 'total_clicks': 0, 'button_stats': []}

def get_active_users_for_newsletter() -> List[int]:
    """Получает список ID активных пользователей для рассылки."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE status != 'redeemed_and_left'")
        user_ids = [row[0] for row in cur.fetchall()]
        conn.close()
        return user_ids
    except Exception as e:
        logging.error(f"Ошибка получения списка пользователей для рассылки: {e}")
        return []

# --- Функции для работы с Персоналом (staff) ---

def find_staff_by_telegram_id(telegram_id: int) -> Optional[sqlite3.Row]:
    """Находит сотрудника по его Telegram ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (telegram_id,))
        staff_member = cur.fetchone()
        conn.close()
        return staff_member
    except Exception as e:
        logging.error(f"Ошибка поиска сотрудника по Telegram ID {telegram_id}: {e}")
        return None

def find_staff_by_code(unique_code: str) -> Optional[sqlite3.Row]:
    """Находит сотрудника по его уникальному коду."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (unique_code,))
        staff_member = cur.fetchone()
        conn.close()
        return staff_member
    except Exception as e:
        logging.error(f"Ошибка поиска сотрудника по коду {unique_code}: {e}")
        return None

def add_or_update_staff(telegram_id: int, full_name: str, position: str, username: str = None) -> Optional[str]:
    """Добавляет нового сотрудника или обновляет данные существующего."""
    try:
        parts = full_name.split()
        short_name = f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]
        
        # Генерируем уникальный код на основе username (если есть) или имени
        if username:
            # Используем username для генерации кода
            base_code = username.lower().replace('@', '').replace('_', '').replace('-', '')
            # Добавляем последние цифры telegram_id для уникальности
            unique_code = f"{base_code}{telegram_id % 1000}"
        else:
            # Если нет username, используем имя (на кириллице)
            base_code = parts[0].lower().strip().replace(' ', '')
            unique_code = f"{base_code}{telegram_id % 1000}"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO staff (telegram_id, full_name, short_name, position, unique_code, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (telegram_id, full_name, short_name, position, unique_code)
        )
        conn.commit()
        conn.close()
        logging.info(f"Сотрудник {full_name} (ID: {telegram_id}) успешно добавлен/обновлен в системе.")
        return unique_code
    except Exception as e:
        logging.error(f"Ошибка при добавлении/обновлении сотрудника {telegram_id}: {e}")
        return None

def get_all_staff(only_active: bool = False) -> List[sqlite3.Row]:
    """Возвращает список всех или только активных сотрудников."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT * FROM staff ORDER BY full_name"
        if only_active:
            query = "SELECT * FROM staff WHERE status = 'active' ORDER BY full_name"
        cur.execute(query)
        staff_list = cur.fetchall()
        conn.close()
        return staff_list
    except Exception as e:
        logging.error(f"Ошибка получения списка сотрудников: {e}")
        return []

def update_staff_status(staff_id: int, new_status: str) -> bool:
    """Обновляет статус сотрудника (active/inactive)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE staff SET status = ? WHERE staff_id = ?", (new_status, staff_id))
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        logging.info(f"Статус сотрудника {staff_id} обновлен на {new_status}.")
        return updated
    except Exception as e:
        logging.error(f"Ошибка обновления статуса сотрудника {staff_id}: {e}")
        return False
        
def get_staff_performance_for_period(start_time: datetime, end_time: datetime) -> Dict[str, List[Dict]]:
    """Собирает статистику по персоналу за период."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Конвертируем datetime в строку формата, подходящего для текущей БД
        start_str = _format_dt_for_db(start_time)
        end_str = _format_dt_for_db(end_time)
        
        cur.execute("""
            SELECT s.short_name, s.position, u.status
            FROM users u
            JOIN staff s ON u.brought_by_staff_id = s.staff_id
            WHERE u.signup_date BETWEEN ? AND ?
        """, (start_str, end_str))
        
        results = cur.fetchall()
        conn.close()

        performance = {}
        for row in results:
            name = row['short_name']
            if name not in performance:
                performance[name] = {'position': row['position'], 'brought': 0, 'churn': 0}
            
            performance[name]['brought'] += 1
            if row['status'] == 'redeemed_and_left':
                performance[name]['churn'] += 1
        
        grouped_performance = {}
        for name, data in performance.items():
            position = data['position']
            if position not in grouped_performance:
                grouped_performance[position] = []
            grouped_performance[position].append({'name': name, 'brought': data['brought'], 'churn': data['churn']})
            
        for position in grouped_performance:
            grouped_performance[position].sort(key=lambda x: x['brought'], reverse=True)
        
        return grouped_performance
    except Exception as e:
        logging.error(f"Ошибка получения статистики по персоналу: {e}")
        return {}

def get_staff_qr_diagnostics_for_period(start_time: datetime, end_time: datetime) -> Dict:
    """Получает детальную диагностику по QR-кодам сотрудников за период."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Конвертируем datetime в строку формата, подходящего для текущей БД
        start_str = _format_dt_for_db(start_time)
        end_str = _format_dt_for_db(end_time)
        
        # Получаем всех активных сотрудников
        cur.execute("SELECT staff_id, full_name, short_name, unique_code, position FROM staff WHERE status = 'active'")
        active_staff = cur.fetchall()
        
        # Получаем успешные переходы по QR-кодам сотрудников
        cur.execute("""
            SELECT u.brought_by_staff_id, s.full_name, s.short_name, s.unique_code, COUNT(*) as count
            FROM users u
            LEFT JOIN staff s ON u.brought_by_staff_id = s.staff_id
            WHERE u.signup_date BETWEEN ? AND ? 
                AND u.source = 'staff'
                AND u.brought_by_staff_id IS NOT NULL
            GROUP BY u.brought_by_staff_id, s.full_name, s.short_name, s.unique_code
            ORDER BY count DESC
        """, (start_str, end_str))
        successful_qr = cur.fetchall()
        
        # Получаем переходы с некорректными кодами
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM users 
            WHERE signup_date BETWEEN ? AND ? 
                AND source LIKE 'Неизвестный_сотрудник_%'
            GROUP BY source
            ORDER BY count DESC
        """, (start_str, end_str))
        invalid_codes = cur.fetchall()
        
        # Получаем переходы "direct", которые могли быть некорректными QR-кодами
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE signup_date BETWEEN ? AND ? 
                AND source = 'direct'
        """, (start_str, end_str))
        direct_count = cur.fetchone()['count']
        
        conn.close()
        
        return {
            'active_staff': [dict(row) for row in active_staff],
            'successful_qr': [dict(row) for row in successful_qr],
            'invalid_codes': [dict(row) for row in invalid_codes],
            'direct_count': direct_count
        }
    except Exception as e:
        logging.error(f"Ошибка получения диагностики QR-кодов: {e}")
        return {
            'active_staff': [],
            'successful_qr': [],
            'invalid_codes': [],
            'direct_count': 0
        }

def get_staff_leaderboard(start_time: datetime, end_time: datetime, limit: int = 10) -> list:
    """Получает топ самых активных сотрудников за период."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Конвертируем datetime в строку формата, подходящего для текущей БД
        start_str = _format_dt_for_db(start_time)
        end_str = _format_dt_for_db(end_time)
        
        # Получаем статистику по каждому сотруднику
        cur.execute("""
            SELECT 
                s.staff_id,
                s.full_name,
                s.short_name,
                s.position,
                s.unique_code,
                COUNT(u.user_id) as attracted_users,
                COUNT(CASE WHEN u.status IN ('issued', 'redeemed', 'redeemed_and_left') THEN 1 END) as issued_coupons,
                COUNT(CASE WHEN u.status IN ('redeemed', 'redeemed_and_left') THEN 1 END) as redeemed_coupons
            FROM staff s
            LEFT JOIN users u ON s.staff_id = u.brought_by_staff_id 
                AND u.source = 'staff'
                AND u.signup_date BETWEEN ? AND ?
            WHERE s.status = 'active'
            GROUP BY s.staff_id, s.full_name, s.short_name, s.position, s.unique_code
            ORDER BY attracted_users DESC, issued_coupons DESC
            LIMIT ?
        """, (start_str, end_str, limit))
        
        staff_stats = cur.fetchall()
        conn.close()
        
        return [dict(row) for row in staff_stats]
        
    except Exception as e:
        logging.error(f"Ошибка получения топа сотрудников: {e}")
        return []

def get_staff_monthly_stats(year: int, month: int) -> list:
    """Получает статистику сотрудников за конкретный месяц."""
    try:
        from datetime import datetime, timedelta
        import calendar
        
        # Определяем начало и конец месяца
        start_date = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        return get_staff_leaderboard(start_date, end_date, limit=50)
        
    except Exception as e:
        logging.error(f"Ошибка получения месячной статистики: {e}")
        return []

def get_staff_period_stats(start_time: datetime, end_time: datetime) -> dict:
    """Получает общую статистику по сотрудникам за период."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Конвертируем datetime в строку формата, подходящего для текущей БД
        start_str = _format_dt_for_db(start_time)
        end_str = _format_dt_for_db(end_time)
        
        # Получаем общие данные за период
        cur.execute("""
            SELECT 
                COUNT(u.user_id) as total_attracted,
                COUNT(CASE WHEN u.status IN ('issued', 'redeemed', 'redeemed_and_left') THEN 1 END) as total_issued,
                COUNT(CASE WHEN u.status IN ('redeemed', 'redeemed_and_left') THEN 1 END) as total_redeemed,
                COUNT(DISTINCT u.brought_by_staff_id) as active_staff_count
            FROM users u
            INNER JOIN staff s ON u.brought_by_staff_id = s.staff_id
            WHERE u.source = 'staff'
                AND u.signup_date BETWEEN ? AND ?
                AND s.status = 'active'
        """, (start_str, end_str))
        
        result = cur.fetchone()
        conn.close()
        
        return dict(result) if result else {}
        
    except Exception as e:
        logging.error(f"Ошибка получения статистики за период: {e}")
        return {}


def get_all_users() -> List[Dict[str, Any]]:
    """
    Получает всех пользователей из базы данных.
    Возвращает список словарей с данными пользователей.
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                user_id,
                first_name,
                username, 
                real_name,
                phone_number,
                birth_date,
                status,
                source,
                signup_date,
                contact_shared_date,
                redeem_date,
                profile_completed,
                ai_concept
            FROM users 
            ORDER BY signup_date DESC
        """)
        
        users = []
        for row in cur.fetchall():
            users.append(dict(row))
        
        conn.close()
        return users
        
    except Exception as e:
        logging.error(f"Ошибка получения всех пользователей: {e}")
        return []


def get_all_users_for_report() -> List[Dict[str, Any]]:
    """
    Получает всех пользователей для полного отчета статистики.
    Возвращает список словарей с данными пользователей.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                user_id,
                first_name,
                username, 
                status,
                source,
                utm_source,
                utm_medium,
                utm_campaign,
                signup_date,
                redeem_date,
                referrer_id,
                brought_by_staff_id,
                registration_time
            FROM users 
            ORDER BY signup_date ASC
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        # Преобразуем в список словарей
        users = []
        for row in rows:
            user_dict = dict(row)
            users.append(user_dict)
        
        return users
        
    except Exception as e:
        logging.error(f"Ошибка получения всех пользователей для отчета: {e}")
        return []


def get_all_users_for_broadcast():
    """
    Получает список всех пользователей для рассылки (исключая заблокировавших бота)
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.get_all_users_for_broadcast()
        
        # SQLite версия
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Получаем всех активных пользователей (не заблокировавших бота)
        cur.execute("""
            SELECT user_id, username, first_name, signup_date
            FROM users 
            WHERE (blocked IS NULL OR blocked = 0)
            AND user_id IS NOT NULL
            ORDER BY signup_date DESC
        """)
        
        users = []
        for row in cur.fetchall():
            users.append({
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2], 
                'signup_date': row[3]
            })
        
        conn.close()
        logging.info(f"Найдено {len(users)} пользователей для рассылки")
        return users
        
    except Exception as e:
        logging.error(f"Ошибка получения пользователей для рассылки: {e}")
        return []


def mark_user_blocked(user_id):
    """
    Отмечает пользователя как заблокировавшего бота
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.mark_user_blocked(user_id)
        
        # SQLite версия
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE users 
            SET blocked = 1, block_date = ?
            WHERE user_id = ?
        """, (datetime.datetime.now(pytz.utc).isoformat(), user_id))
        
        conn.commit()
        success = cur.rowcount > 0
        conn.close()
        
        if success:
            logging.info(f"Пользователь {user_id} отмечен как заблокировавший бота")
        
        return success
        
    except Exception as e:
        logging.error(f"Ошибка отметки блокировки пользователя {user_id}: {e}")
        return False


def get_broadcast_statistics():
    """
    Получает статистику для рассылок
    """
    try:
        if USE_POSTGRES and pg_client:
            return pg_client.get_broadcast_statistics()
        
        # SQLite версия
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Общее количество пользователей
        cur.execute("SELECT COUNT(*) FROM users WHERE user_id IS NOT NULL")
        total_users = cur.fetchone()[0]
        
        # Активные пользователи (не заблокировавшие бота)
        cur.execute("SELECT COUNT(*) FROM users WHERE (blocked IS NULL OR blocked = 0) AND user_id IS NOT NULL")
        active_users = cur.fetchone()[0]
        
        # Заблокировавшие бота
        cur.execute("SELECT COUNT(*) FROM users WHERE blocked = 1")
        blocked_users = cur.fetchone()[0]
        
        # Пользователи за последние 30 дней
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE user_id IS NOT NULL 
            AND julianday('now') - julianday(signup_date) <= 30
        """)
        recent_users = cur.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total_users,
            'active': active_users,
            'blocked': blocked_users,
            'recent_30d': recent_users
        }
        
    except Exception as e:
        logging.error(f"Ошибка получения статистики рассылки: {e}")
        return None
