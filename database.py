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
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# --- Настройки ---
DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "evgenich_data.db")
SHEET_NAME = "Выгрузка Пользователей"

# --- Секция работы с Google Sheets (фоновые задачи) ---
def _get_sheets_worksheet():
    """Подключается к Google Sheets и возвращает рабочий лист."""
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
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            worksheet.append_row(row_data)
            logging.info(f"G-Sheets (фон) | Пользователь с ID {row_data[1]} успешно дублирован.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка дублирования пользователя {row_data[1]}: {e}")

def _update_status_in_sheets_in_background(user_id: int, new_status: str, redeem_time: Optional[datetime.datetime]):
    """(Фоновая задача) Обновляет статус пользователя в таблице."""
    try:
        worksheet = _get_sheets_worksheet()
        if worksheet:
            cell = worksheet.find(str(user_id), in_column=2)
            if cell:
                worksheet.update_cell(cell.row, 5, new_status)
                if redeem_time:
                    worksheet.update_cell(cell.row, 8, redeem_time.strftime('%Y-%m-%d %H:%M:%S'))
                logging.info(f"G-Sheets (фон) | Статус пользователя {user_id} успешно обновлен.")
            else:
                logging.warning(f"G-Sheets (фон) | Не удалось найти пользователя {user_id} для обновления.")
    except Exception as e:
        logging.error(f"G-Sheets (фон) | Ошибка обновления статуса для {user_id}: {e}")

# --- Секция работы с локальной базой SQLite ---
def get_db_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT, first_name TEXT,
                status TEXT DEFAULT 'registered',
                source TEXT, referrer_id INTEGER,
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeem_date TIMESTAMP,
                last_check_date TIMESTAMP
            )""")
        conn.commit()
        try:
            cur.execute("SELECT last_check_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            logging.info("Обновляю структуру таблицы 'users', добавляю 'last_check_date'...")
            cur.execute("ALTER TABLE users ADD COLUMN last_check_date TIMESTAMP")
            conn.commit()
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
        conn.close()
        logging.info("База данных SQLite успешно инициализирована.")
    except Exception as e:
        logging.critical(f"Не удалось инициализировать базу данных SQLite: {e}")


def add_new_user(user_id: int, username: str, first_name: str, source: str, referrer_id: Optional[int] = None):
    signup_time = datetime.datetime.now(pytz.utc)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, source, referrer_id, signup_date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username or "N/A", first_name, source, referrer_id, signup_time)
        )
        conn.commit()
        conn.close()
        logging.info(f"SQLite | Пользователь {user_id} добавлен. Источник: {source}")
    except Exception as e:
        logging.error(f"SQLite | Ошибка добавления пользователя {user_id}: {e}")
        return
    row_data = [
        signup_time.strftime('%Y-%m-%d %H:%M:%S'), user_id, first_name,
        username or "N/A", 'registered', source,
        referrer_id if referrer_id else "", ""
    ]
    threading.Thread(target=_add_user_to_sheets_in_background, args=(row_data,)).start()

def update_status(user_id: int, new_status: str) -> bool:
    redeem_time = datetime.datetime.now(pytz.utc) if new_status == 'redeemed' else None
    updated = False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if redeem_time:
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
    if updated:
        threading.Thread(target=_update_status_in_sheets_in_background, args=(user_id, new_status, redeem_time)).start()
    return updated

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

def get_reward_status(user_id: int) -> str:
    user = find_user_by_id(user_id)
    return user['status'] if user else 'not_found'

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
