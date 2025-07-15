# database.py
"""
Модуль для управления базой данных SQLite с асинхронным дублированием в Google Sheets.
"""
import sqlite3
import logging
from typing import Optional, Tuple, List, Dict, Any
import datetime
import pytz
import os
import json
import gspread
import threading
from collections import defaultdict
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# --- Настройки ---
DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "evgenich_data.db")
SHEET_NAME = "Выгрузка Пользователей"

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
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        return spreadsheet.worksheet(SHEET_NAME)
    except Exception as e:
        logging.error(f"G-Sheets | Не удалось подключиться к таблице '{SHEET_NAME}': {e}")
        return None

def _add_user_to_sheets_in_background(row_data: List[Any]):
    """(Фоновая задача) Добавляет строку с данными пользователя в таблицу."""
    if not GOOGLE_SHEETS_ENABLED:
        return
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            worksheet.append_row(row_data)
            logging.info(f"G-Sheets (фон) | Пользователь с ID {row_data[1]} успешно дублирован.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка дублирования пользователя {row_data[1]}: {e}")

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
                    worksheet.update_cell(cell.row, 10, redeem_time.strftime('%Y-%m-%d %H:%M:%S'))  # Дата погашения в колонке J (10)
                logging.info(f"G-Sheets (фон) | Статус пользователя {user_id} успешно обновлен на '{russian_status}'.")
            else:
                logging.warning(f"G-Sheets (фон) | Не удалось найти пользователя {user_id} для обновления.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка обновления статуса для {user_id}: {e}")

# --- Секция работы с локальной базой SQLite ---
def get_db_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
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
            logging.info("База данных обновлена: добавлена колонка phone_number")

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
            
        conn.commit()
        conn.close()
        logging.info("База данных SQLite успешно инициализирована/обновлена.")
    except Exception as e:
        logging.critical(f"Не удалось инициализировать базу данных SQLite: {e}")

# --- Функции для работы с Пользователями (users) ---

def add_new_user(user_id: int, username: str, first_name: str, source: str, referrer_id: Optional[int] = None, brought_by_staff_id: Optional[int] = None):
    """Добавляет нового пользователя, возможно с привязкой к сотруднику."""
    signup_time = datetime.datetime.now(pytz.utc)
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
    row_data = [
        signup_time.strftime('%Y-%m-%d %H:%M:%S'), user_id, first_name,
        username or "N/A", "", "", "",  # phone_number, real_name, birth_date пока пустые
        _translate_status_to_russian('registered'), source, ""  # дата погашения пока пустая
    ]
    if GOOGLE_SHEETS_ENABLED:
        threading.Thread(target=_add_user_to_sheets_in_background, args=(row_data,)).start()

def update_status(user_id: int, new_status: str) -> bool:
    redeem_time = datetime.datetime.now(pytz.utc) if new_status == 'redeemed' else None
    updated = False
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
        cur.execute(
            "UPDATE users SET phone_number = ?, contact_shared_date = ? WHERE user_id = ?",
            (phone_number, contact_time, user_id)
        )
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        if updated:
            logging.info(f"SQLite | Контакт пользователя {user_id} обновлен: {phone_number}")
            # Обновляем в Google Sheets в фоновом режиме
            if GOOGLE_SHEETS_ENABLED:
                threading.Thread(target=_update_contact_in_sheets_in_background, args=(user_id, phone_number, contact_time)).start()
        return updated
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления контакта для {user_id}: {e}")
        return False

def update_user_name(user_id: int, real_name: str) -> bool:
    """Обновляет настоящее имя пользователя."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET real_name = ? WHERE user_id = ?",
            (real_name, user_id)
        )
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        if updated:
            logging.info(f"SQLite | Имя пользователя {user_id} обновлено: {real_name}")
            # Обновляем в Google Sheets в фоновом режиме
            if GOOGLE_SHEETS_ENABLED:
                threading.Thread(target=_update_name_in_sheets_in_background, args=(user_id, real_name)).start()
        return updated
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления имени для {user_id}: {e}")
        return False

def update_user_birth_date(user_id: int, birth_date: str) -> bool:
    """Обновляет дату рождения пользователя."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET birth_date = ?, profile_completed = 1 WHERE user_id = ?",
            (birth_date, user_id)
        )
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        if updated:
            logging.info(f"SQLite | Дата рождения пользователя {user_id} обновлена: {birth_date}")
            # Обновляем в Google Sheets в фоновом режиме
            if GOOGLE_SHEETS_ENABLED:
                threading.Thread(target=_update_birth_date_in_sheets_in_background, args=(user_id, birth_date)).start()
        return updated
    except Exception as e:
        logging.error(f"SQLite | Ошибка обновления даты рождения для {user_id}: {e}")
        return False

def find_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()
        conn.close()
        return user
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
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ? AND status IN ('redeemed', 'redeemed_and_left')", (start_time, end_time))
        redeemed_total = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ? AND status = 'redeemed_and_left'",
            (start_time, end_time)
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
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? AND status IN ('issued', 'redeemed', 'redeemed_and_left')", (start_time, end_time))
        issued_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ?", (start_time, end_time))
        redeemed_count = cur.fetchone()[0]
        cur.execute("SELECT source, COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? GROUP BY source", (start_time, end_time))
        sources = {row['source']: row['COUNT(*)'] for row in cur.fetchall()}
        total_redeem_time_seconds = 0
        if redeemed_count > 0:
            cur.execute("SELECT SUM(strftime('%s', redeem_date) - strftime('%s', signup_date)) FROM users WHERE redeem_date BETWEEN ? AND ? AND status IN ('redeemed', 'redeemed_and_left')", (start_time, end_time))
            total_redeem_time_seconds_row = cur.fetchone()[0]
            total_redeem_time_seconds = total_redeem_time_seconds_row or 0
        conn.close()
        return issued_count, redeemed_count, [], sources, total_redeem_time_seconds
    except Exception as e:
        logging.error(f"Ошибка сбора данных для отчета в SQLite: {e}")
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

def add_or_update_staff(telegram_id: int, full_name: str, position: str) -> Optional[str]:
    """Добавляет нового сотрудника или обновляет данные существующего."""
    try:
        parts = full_name.split()
        short_name = f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]
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
        cur.execute("""
            SELECT s.short_name, s.position, u.status
            FROM users u
            JOIN staff s ON u.brought_by_staff_id = s.staff_id
            WHERE u.signup_date BETWEEN ? AND ?
        """, (start_time, end_time))
        
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
        logging.error(f"Ошибка сбора статистики по персоналу: {e}")
        return {}
