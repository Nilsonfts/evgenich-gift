import sqlite3
import logging
from datetime import datetime

def init_db():
    """Создает базу данных и таблицу, если их нет."""
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    # Добавляем колонку status ('issued', 'redeemed')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            reward_status TEXT DEFAULT 'none',
            reward_date DATETIME
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("База данных 'guests.db' успешно инициализирована.")

def add_user(user_id: int, username: str, first_name: str):
    """Добавляет нового пользователя в базу, если его там еще нет."""
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                   (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_reward_status(user_id: int) -> str:
    """Проверяет статус награды пользователя."""
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    cursor.execute("SELECT reward_status FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'none'

def grant_reward(user_id: int):
    """Отмечает в базе, что пользователю 'выдана' награда (но еще не погашена)."""
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET reward_status = 'issued', reward_date = ? WHERE user_id = ?",
                   (datetime.now(), user_id))
    conn.commit()
    conn.close()

def redeem_reward(user_id: int) -> bool:
    """Погашает награду. Возвращает True если успешно, иначе False."""
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    # Убедимся, что погашаем только 'выданную' награду
    cursor.execute("SELECT reward_status FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result and result[0] == 'issued':
        cursor.execute("UPDATE users SET reward_status = 'redeemed' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False
