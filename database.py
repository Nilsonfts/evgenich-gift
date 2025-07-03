# database.py
import sqlite3
import logging
from datetime import datetime

def init_db():
    """Создает базу данных и таблицу, если их нет."""
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        # Создаем таблицу users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                has_received_reward BOOLEAN NOT NULL DEFAULT 0,
                reward_date DATETIME
            )
        [cite_start]''') # [cite: 7]
        conn.commit()
        conn.close()
        [cite_start]logging.info("База данных 'guests.db' успешно инициализирована.") # [cite: 7]
    except Exception as e:
        [cite_start]logging.error(f"Ошибка при инициализации БД: {e}") # [cite: 7]

def user_exists(user_id: int) -> bool:
    [cite_start]"""Проверяет, есть ли пользователь в базе.""" # [cite: 7]
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        [cite_start]cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) # [cite: 7]
        [cite_start]result = cursor.fetchone() # [cite: 7]
        conn.close()
        return result is not None
    except Exception as e:
        [cite_start]logging.error(f"Ошибка при проверке пользователя {user_id}: {e}") # [cite: 7]
        return False

def add_user(user_id: int, username: str, first_name: str):
    [cite_start]"""Добавляет нового пользователя в базу, если его там нет.""" # [cite: 7]
    if user_exists(user_id):
        return
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                       [cite_start](user_id, username, first_name)) # [cite: 7]
        conn.commit()
        conn.close()
    except Exception as e:
        [cite_start]logging.error(f"Ошибка при добавлении пользователя {user_id}: {e}") # [cite: 7]

def check_reward_status(user_id: int) -> bool:
    [cite_start]"""Проверяет, получал ли пользователь уже награду.""" # [cite: 7]
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        [cite_start]cursor.execute("SELECT has_received_reward FROM users WHERE user_id = ?", (user_id,)) # [cite: 7]
        [cite_start]result = cursor.fetchone() # [cite: 7]
        conn.close()
        return result[0] == 1 if result else False
    except Exception as e:
        [cite_start]logging.error(f"Ошибка при проверке награды у {user_id}: {e}") # [cite: 7]
        return True

def grant_reward(user_id: int):
    [cite_start]"""Отмечает в базе, что пользователь получил награду.""" # [cite: 7]
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET has_received_reward = 1, reward_date = ? WHERE user_id = ?",
                       [cite_start](datetime.now(), user_id)) # [cite: 7]
        conn.commit()
        conn.close()
    except Exception as e:
        [cite_start]logging.error(f"Ошибка при выдаче награды пользователю {user_id}: {e}") # [cite: 7]
