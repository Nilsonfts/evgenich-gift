# games.py
"""
Модуль для мини-игр: викторины, колесо фортуны и другие развлечения для гостей.
"""

import random
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger("evgenich_games")

# --- ВИКТОРИНЫ ---

QUIZ_QUESTIONS = [
    {
        "question": "Какая самая популярная настойка в нашем баре?",
        "options": ["Кедровка", "Хреновуха", "Клюквенная", "Перцовка"],
        "correct": 0,
        "explanation": "Кедровка - наш хит! Готовится по старинному рецепту с кедровыми орешками 🌰"
    },
    {
        "question": "В каком году группа 'Руки Вверх!' выпустила хит 'Крошка моя'?",
        "options": ["1995", "1997", "1999", "2001"],
        "correct": 1,
        "explanation": "1997 год! Золотое время русской поп-музыки 🎵"
    },
    {
        "question": "Какая закуска лучше всего подходит к настойкам?",
        "options": ["Селедка под шубой", "Соленые огурчики", "Сало с чесноком", "Все перечисленное"],
        "correct": 3,
        "explanation": "Правильно! К настойкам подходят все традиционные русские закуски 🥒"
    },
    {
        "question": "Сколько градусов в классической русской настойке?",
        "options": ["25-30°", "35-40°", "45-50°", "55-60°"],
        "correct": 1,
        "explanation": "35-40° - идеальная крепость для настоек. Не слишком крепко, но с характером! 🥃"
    },
    {
        "question": "Как правильно пить настойку?",
        "options": ["Залпом", "Маленькими глотками", "Разбавлять водой", "С закуской"],
        "correct": 1,
        "explanation": "Настойку нужно смаковать маленькими глотками, чтобы почувствовать все нюансы вкуса 😋"
    }
]

WHEEL_PRIZES = [
    {"name": "Бесплатная рюмка настойки", "probability": 15, "type": "drink"},
    {"name": "Скидка 20% на следующий заказ", "probability": 20, "type": "discount"},
    {"name": "Комплимент от заведения", "probability": 25, "type": "treat"},
    {"name": "Сертификат на 500₽", "probability": 5, "type": "certificate"},
    {"name": "Фирменная рюмка в подарок", "probability": 10, "type": "souvenir"},
    {"name": "Участие в закрытой дегустации", "probability": 8, "type": "event"},
    {"name": "Удача в следующий раз!", "probability": 17, "type": "nothing"}
]

def get_random_quiz_question() -> Dict[str, Any]:
    """Возвращает случайный вопрос для викторины."""
    return random.choice(QUIZ_QUESTIONS)

def check_quiz_answer(question_index: int, user_answer: int) -> Dict[str, Any]:
    """
    Проверяет ответ пользователя на вопрос викторины.
    
    Args:
        question_index: Индекс вопроса в списке QUIZ_QUESTIONS
        user_answer: Индекс выбранного ответа (0-3)
    
    Returns:
        Dict с результатом проверки
    """
    if question_index >= len(QUIZ_QUESTIONS):
        return {"error": "Неверный индекс вопроса"}
    
    question = QUIZ_QUESTIONS[question_index]
    is_correct = user_answer == question["correct"]
    
    return {
        "is_correct": is_correct,
        "correct_answer": question["options"][question["correct"]],
        "explanation": question["explanation"],
        "reward": "🎉 +50 баллов!" if is_correct else "😔 +10 баллов за участие"
    }

def spin_wheel_of_fortune() -> Dict[str, Any]:
    """
    Крутит колесо фортуны и возвращает выигрыш.
    
    Returns:
        Dict с результатом розыгрыша
    """
    # Генерируем случайное число от 0 до 100
    spin_result = random.randint(1, 100)
    
    # Определяем приз на основе вероятностей
    cumulative_probability = 0
    for prize in WHEEL_PRIZES:
        cumulative_probability += prize["probability"]
        if spin_result <= cumulative_probability:
            return {
                "prize": prize["name"],
                "type": prize["type"],
                "message": f"🎰 Поздравляем! Вы выиграли: {prize['name']}!",
                "claim_code": generate_claim_code(prize["type"])
            }
    
    # Если что-то пошло не так, возвращаем утешительный приз
    return {
        "prize": "Удача в следующий раз!",
        "type": "nothing",
        "message": "🎰 В этот раз не повезло, но не расстраивайтесь! Попробуйте еще раз завтра.",
        "claim_code": None
    }

def generate_claim_code(prize_type: str) -> str:
    """Генерирует код для получения приза."""
    if prize_type == "nothing":
        return None
    
    timestamp = datetime.now().strftime("%H%M%S")
    random_part = random.randint(100, 999)
    return f"{prize_type.upper()[:3]}{timestamp}{random_part}"

# --- УПРАВЛЕНИЕ ИГРАМИ В БАЗЕ ДАННЫХ ---

def save_game_result(user_id: int, game_type: str, result: Dict[str, Any]) -> bool:
    """
    Сохраняет результат игры в базу данных.
    
    Args:
        user_id: ID пользователя
        game_type: Тип игры ("quiz" или "wheel")
        result: Результат игры
    
    Returns:
        True если сохранено успешно
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        cur = conn.cursor()
        
        # Создаем таблицу для игр, если её нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                result TEXT NOT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                claim_code TEXT,
                is_claimed BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Сохраняем результат
        import json
        cur.execute("""
            INSERT INTO game_results (user_id, game_type, result, claim_code)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            game_type,
            json.dumps(result, ensure_ascii=False),
            result.get("claim_code")
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Сохранен результат игры {game_type} для пользователя {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения результата игры: {e}")
        return False

def get_user_game_stats(user_id: int) -> Dict[str, Any]:
    """
    Получает статистику игр пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Dict со статистикой игр
    """
    try:
        import database
        import sqlite3
        import json
        
        conn = sqlite3.connect(database.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Получаем все игры пользователя
        cur.execute("""
            SELECT game_type, result, played_at, is_claimed
            FROM game_results
            WHERE user_id = ?
            ORDER BY played_at DESC
        """, (user_id,))
        
        games = cur.fetchall()
        conn.close()
        
        if not games:
            return {
                "total_games": 0,
                "quiz_games": 0,
                "wheel_spins": 0,
                "quiz_correct": 0,
                "prizes_won": 0,
                "unclaimed_prizes": 0
            }
        
        stats = {
            "total_games": len(games),
            "quiz_games": 0,
            "wheel_spins": 0,
            "quiz_correct": 0,
            "prizes_won": 0,
            "unclaimed_prizes": 0
        }
        
        for game in games:
            result = json.loads(game["result"])
            
            if game["game_type"] == "quiz":
                stats["quiz_games"] += 1
                if result.get("is_correct"):
                    stats["quiz_correct"] += 1
            elif game["game_type"] == "wheel":
                stats["wheel_spins"] += 1
                if result.get("type") != "nothing":
                    stats["prizes_won"] += 1
                    if not game["is_claimed"]:
                        stats["unclaimed_prizes"] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики игр для пользователя {user_id}: {e}")
        return {"error": "Не удалось загрузить статистику"}

def can_play_game(user_id: int, game_type: str) -> Dict[str, Any]:
    """
    Проверяет, может ли пользователь играть в игру (ограничения по времени).
    
    Args:
        user_id: ID пользователя
        game_type: Тип игры
    
    Returns:
        Dict с информацией о возможности игры
    """
    try:
        import database
        import sqlite3
        
        conn = sqlite3.connect(database.DB_FILE)
        cur = conn.cursor()
        
        # Проверяем последнюю игру этого типа
        cur.execute("""
            SELECT played_at FROM game_results
            WHERE user_id = ? AND game_type = ?
            ORDER BY played_at DESC
            LIMIT 1
        """, (user_id, game_type))
        
        last_game = cur.fetchone()
        conn.close()
        
        if not last_game:
            return {"can_play": True, "message": "Добро пожаловать в игру!"}
        
        # Парсим время последней игры
        last_play_time = datetime.fromisoformat(last_game[0].replace(' ', 'T'))
        now = datetime.now()
        
        # Ограничения: викторина - раз в час, колесо - раз в 3 часа
        cooldown_hours = 1 if game_type == "quiz" else 3
        time_since_last = now - last_play_time
        
        if time_since_last < timedelta(hours=cooldown_hours):
            remaining_time = timedelta(hours=cooldown_hours) - time_since_last
            hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
            minutes = remainder // 60
            
            return {
                "can_play": False,
                "message": f"⏰ Следующая игра будет доступна через {hours}ч {minutes}мин"
            }
        
        return {"can_play": True, "message": "Можно играть!"}
        
    except Exception as e:
        logger.error(f"Ошибка проверки возможности игры: {e}")
        return {"can_play": True, "message": "Добро пожаловать в игру!"}
