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
import threading  # <--- ДОБАВЛЕНО: Для фоновых задач
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# --- Настройки ---
DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "evgenich_data.db")
SHEET_NAME = "Выгрузка Пользователей"

# --- Секция работы с Google Sheets (теперь для фоновых задач) ---

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
    """Возвращает соединение с локальной БД."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует локальную базу данных и создает таблицы."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Таблица пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                status TEXT DEFAULT 'registered',
                source TEXT,
                referrer_id INTEGER,
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeem_date TIMESTAMP
            )
        """)
        # Таблица для истории диалогов AI
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица для обратной связи
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rating INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logging.info("База данных SQLite успешно инициализирована.")
    except Exception as e:
        logging.critical(f"Не удалось инициализировать базу данных SQLite: {e}")

# --- Функции с асинхронным дублированием ---

def add_new_user(user_id: int, username: str, first_name: str, source: str, referrer_id: Optional[int] = None):
    """
    Добавляет нового пользователя в SQLite и запускает фоновую выгрузку в Google Sheets.
    """
    signup_time = datetime.datetime.now(pytz.utc)
    
    # 1. Быстрая запись в локальную базу
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

    # 2. Подготовка данных и запуск медленной выгрузки в фоне
    row_data = [
        signup_time.strftime('%Y-%m-%d %H:%M:%S'), user_id, first_name,
        username or "N/A", 'registered', source,
        referrer_id if referrer_id else "", ""
    ]
    # Создаем и запускаем фоновый поток
    threading.Thread(target=_add_user_to_sheets_in_background, args=(row_data,)).start()

def update_status(user_id: int, new_status: str) -> bool:
    """
    Обновляет статус в SQLite и запускает фоновое обновление в Google Sheets.
    """
    redeem_time = datetime.datetime.now(pytz.utc) if new_status == 'redeemed' else None
    updated = False
    
    # 1. Быстрое обновление в локальной базе
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if redeem_time:
            cur.execute("UPDATE users SET status = ?, redeem_date = ? WHERE user_id = ?", (new_status, redeem_time, user_id))
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

    # 2. Запуск медленного обновления в фоне, только если локальное прошло успешно
    if updated:
        threading.Thread(target=_update_status_in_sheets_in_background, args=(user_id, new_status, redeem_time)).start()
            
    return updated

# --- Остальные функции (работают только с быстрой локальной базой) ---

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
        
def get_report_data_for_period(start_time: datetime.datetime, end_time: datetime.datetime) -> tuple:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? AND status IN ('issued', 'redeemed')",
            (start_time, end_time)
        )
        issued_count = cur.fetchone()[0]

        cur.execute(
            "SELECT * FROM users WHERE signup_date BETWEEN ? AND ? AND status = 'redeemed' AND redeem_date IS NOT NULL",
            (start_time, end_time)
        )
        redeemed_users_rows = cur.fetchall()
        redeemed_count = len(redeemed_users_rows)
        
        redeemed_users_list = [f"@{row['username']}" if row['username'] != "N/A" else row['first_name'] for row in redeemed_users_rows]
        
        cur.execute("SELECT source, COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? GROUP BY source", (start_time, end_time))
        sources = {row['source']: row['COUNT(*)'] for row in cur.fetchall()}
        
        total_redeem_time_seconds = 0
        if redeemed_count > 0:
            cur.execute(
                "SELECT SUM(strftime('%s', redeem_date) - strftime('%s', signup_date)) FROM users WHERE signup_date BETWEEN ? AND ? AND status = 'redeemed'",
                (start_time, end_time)
            )
            total_redeem_time_seconds = cur.fetchone()[0] or 0

        conn.close()
        return issued_count, redeemed_count, redeemed_users_list, sources, total_redeem_time_seconds
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
            WHERE status = 'redeemed' 
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
