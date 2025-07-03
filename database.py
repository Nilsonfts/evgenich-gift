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
        ''')
        conn.commit()
        conn.close()
        logging.info("База данных 'guests.db' успешно инициализирована.")
    except Exception as e:
        logging.error(f"Ошибка при инициализации БД: {e}")

def user_exists(user_id: int) -> bool:
    """Проверяет, есть ли пользователь в базе."""
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logging.error(f"Ошибка при проверке пользователя {user_id}: {e}")
        return False

def add_user(user_id: int, username: str, first_name: str):
    """Добавляет нового пользователя в базу, если его там нет."""
    if user_exists(user_id):
        return
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                       (user_id, username, first_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя {user_id}: {e}")

def check_reward_status(user_id: int) -> bool:
    """Проверяет, получал ли пользователь уже награду."""
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        cursor.execute("SELECT has_received_reward FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        # Если result не None и первый элемент (has_received_reward) равен 1, то True
        return result[0] == 1 if result else False
    except Exception as e:
        logging.error(f"Ошибка при проверке награды у {user_id}: {e}")
        # В случае ошибки лучше считать, что награду уже получали, чтобы избежать злоупотреблений
        return True

def grant_reward(user_id: int):
    """Отмечает в базе, что пользователь получил награду."""
    try:
        conn = sqlite3.connect('guests.db')
        cursor = conn.cursor()
        # Устанавливаем флаг и текущую дату/время
        cursor.execute("UPDATE users SET has_received_reward = 1, reward_date = ? WHERE user_id = ?",
                       (datetime.now(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка при выдаче награды пользователю {user_id}: {e}")
