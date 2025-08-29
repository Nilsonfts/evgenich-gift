# daily_activities.py
"""
Модуль для ежедневных активностей: секретный пароль дня, уведомления о мероприятиях.
"""

import random
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger("evgenich_daily")

# --- СЕКРЕТНЫЙ ПАРОЛЬ ДНЯ ---

PASSWORD_WORDS = [
    "кедровка", "настойка", "евгенич", "душевно", "товарищ", "закуска",
    "рюмочная", "дружище", "подарок", "семьдесят", "винтаж", "атмосфера",
    "квартирник", "старина", "традиция", "гармошка", "застолье", "разговор"
]

def generate_daily_password() -> str:
    """Генерирует пароль дня на основе текущей даты."""
    today = datetime.now()
    # Используем дату как сид для генератора случайных чисел
    random.seed(today.strftime("%Y%m%d"))
    
    # Выбираем случайное слово
    password = random.choice(PASSWORD_WORDS)
    return password

def get_password_of_the_day() -> Dict[str, Any]:
    """
    Возвращает информацию о пароле дня.
    
    Returns:
        Dict с информацией о пароле
    """
    password = generate_daily_password()
    
    return {
        "password": password,
        "date": datetime.now().strftime("%d.%m.%Y"),
        "reward": "🎁 Скидка 15% на любую настойку",
        "hint": f"Пароль состоит из {len(password)} букв и связан с нашим баром",
        "expires_at": datetime.now().replace(hour=23, minute=59, second=59)
    }

def check_daily_password(user_input: str) -> Dict[str, Any]:
    """
    Проверяет правильность введенного пароля дня.
    
    Args:
        user_input: Введенный пользователем пароль
    
    Returns:
        Dict с результатом проверки
    """
    correct_password = generate_daily_password()
    is_correct = user_input.lower().strip() == correct_password.lower()
    
    return {
        "is_correct": is_correct,
        "password": correct_password,
        "reward": "🎁 Скидка 15% на любую настойку" if is_correct else None,
        "message": (
            f"🎉 Правильно! Пароль дня: '{correct_password}'\n\n"
            f"Вы получили скидку 15% на любую настойку!\n"
            f"Покажите это сообщение сотруднику."
        ) if is_correct else f"❌ Неверно! Попробуйте еще раз.\n\nПодсказка: пароль связан с нашим баром и состоит из {len(correct_password)} букв."
    }

def save_password_attempt(user_id: int, password: str, is_correct: bool) -> bool:
    """
    Сохраняет попытку ввода пароля в базу данных.
    
    Args:
        user_id: ID пользователя
        password: Введенный пароль
        is_correct: Правильность пароля
    
    Returns:
        True если сохранено успешно
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        cur = conn.cursor()
        
        # Создаем таблицу для паролей дня, если её нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_password_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                password_attempt TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reward_claimed BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Сохраняем попытку
        cur.execute("""
            INSERT INTO daily_password_attempts (user_id, password_attempt, is_correct)
            VALUES (?, ?, ?)
        """, (user_id, password, is_correct))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Сохранена попытка пароля для пользователя {user_id}: {password} ({'правильно' if is_correct else 'неверно'})")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения попытки пароля: {e}")
        return False

def get_user_password_stats(user_id: int) -> Dict[str, Any]:
    """
    Получает статистику паролей пользователя за сегодня.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Dict со статистикой
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Получаем попытки за сегодня
        cur.execute("""
            SELECT * FROM daily_password_attempts
            WHERE user_id = ? AND DATE(attempted_at) = ?
            ORDER BY attempted_at DESC
        """, (user_id, today))
        
        attempts = cur.fetchall()
        conn.close()
        
        if not attempts:
            return {
                "attempts_today": 0,
                "correct_today": False,
                "can_try": True,
                "last_attempt": None
            }
        
        correct_attempts = [a for a in attempts if a["is_correct"]]
        
        return {
            "attempts_today": len(attempts),
            "correct_today": len(correct_attempts) > 0,
            "can_try": len(correct_attempts) == 0,  # Можно пробовать, если еще не угадал
            "last_attempt": dict(attempts[0]) if attempts else None
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики паролей для пользователя {user_id}: {e}")
        return {"error": "Не удалось загрузить статистику"}

# --- УВЕДОМЛЕНИЯ О МЕРОПРИЯТИЯХ ---

def create_event(title: str, description: str, event_date: datetime, event_type: str = "general") -> Dict[str, Any]:
    """
    Создает новое мероприятие.
    
    Args:
        title: Название мероприятия
        description: Описание
        event_date: Дата и время мероприятия
        event_type: Тип мероприятия (concert, party, tasting, etc.)
    
    Returns:
        Dict с данными созданного мероприятия
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        cur = conn.cursor()
        
        # Создаем таблицу для мероприятий, если её нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TIMESTAMP NOT NULL,
                event_type TEXT DEFAULT 'general',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                max_participants INTEGER,
                current_participants INTEGER DEFAULT 0
            )
        """)
        
        # Создаем мероприятие
        cur.execute("""
            INSERT INTO events (title, description, event_date, event_type)
            VALUES (?, ?, ?, ?)
        """, (title, description, event_date, event_type))
        
        event_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Создано мероприятие: {title} на {event_date}")
        
        return {
            "id": event_id,
            "title": title,
            "description": description,
            "event_date": event_date,
            "event_type": event_type,
            "is_active": True
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания мероприятия: {e}")
        return {"error": "Не удалось создать мероприятие"}

def get_upcoming_events(days_ahead: int = 7) -> list:
    """
    Получает список предстоящих мероприятий.
    
    Args:
        days_ahead: Количество дней вперед для поиска
    
    Returns:
        Список мероприятий
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        end_date = datetime.now() + timedelta(days=days_ahead)
        
        cur.execute("""
            SELECT * FROM events
            WHERE is_active = TRUE 
            AND event_date BETWEEN datetime('now') AND ?
            ORDER BY event_date ASC
        """, (end_date,))
        
        events = cur.fetchall()
        conn.close()
        
        return [dict(event) for event in events]
        
    except Exception as e:
        logger.error(f"Ошибка получения предстоящих мероприятий: {e}")
        return []

def register_for_event(user_id: int, event_id: int) -> Dict[str, Any]:
    """
    Регистрирует пользователя на мероприятие.
    
    Args:
        user_id: ID пользователя
        event_id: ID мероприятия
    
    Returns:
        Dict с результатом регистрации
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        cur = conn.cursor()
        
        # Создаем таблицу для регистраций, если её нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS event_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'registered',
                UNIQUE(user_id, event_id)
            )
        """)
        
        # Проверяем, не зарегистрирован ли уже пользователь
        cur.execute("""
            SELECT id FROM event_registrations
            WHERE user_id = ? AND event_id = ?
        """, (user_id, event_id))
        
        if cur.fetchone():
            conn.close()
            return {
                "success": False,
                "message": "Вы уже зарегистрированы на это мероприятие"
            }
        
        # Регистрируем пользователя
        cur.execute("""
            INSERT INTO event_registrations (user_id, event_id)
            VALUES (?, ?)
        """, (user_id, event_id))
        
        # Обновляем счетчик участников
        cur.execute("""
            UPDATE events 
            SET current_participants = current_participants + 1
            WHERE id = ?
        """, (event_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Пользователь {user_id} зарегистрирован на мероприятие {event_id}")
        
        return {
            "success": True,
            "message": "✅ Вы успешно зарегистрированы на мероприятие!"
        }
        
    except Exception as e:
        logger.error(f"Ошибка регистрации на мероприятие: {e}")
        return {
            "success": False,
            "message": "Не удалось зарегистрироваться. Попробуйте позже."
        }
