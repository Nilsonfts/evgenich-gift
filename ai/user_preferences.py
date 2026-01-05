# /ai/user_preferences.py
"""
Система памяти о предпочтениях пользователя
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger("user_preferences")

PREFERENCES_FILE = "user_preferences.json"

def load_preferences() -> dict:
    """Загружает предпочтения пользователей из файла"""
    try:
        with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки предпочтений: {e}")
        return {}


def save_preferences(preferences: dict):
    """Сохраняет предпочтения пользователей в файл"""
    try:
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения предпочтений: {e}")


def extract_preferences_from_text(user_id: int, text: str):
    """
    Извлекает предпочтения из текста пользователя
    """
    text_lower = text.lower()
    preferences = load_preferences()
    
    if str(user_id) not in preferences:
        preferences[str(user_id)] = {
            "favorite_drinks": [],
            "favorite_food": [],
            "interests": [],
            "dislikes": [],
            "special_dates": [],
            "last_updated": datetime.now().isoformat()
        }
    
    user_prefs = preferences[str(user_id)]
    updated = False
    
    # Напитки
    drinks_keywords = {
        "пиво": ["пиво", "пивко"],
        "вино": ["вино", "винишко"],
        "виски": ["виски", "whisky", "whiskey"],
        "водка": ["водка", "водочка"],
        "коктейль": ["коктейль", "мохито", "маргарита", "дайкири"],
        "настойка": ["настойка", "наливка"],
        "ром": ["ром"],
        "джин": ["джин", "gin"]
    }
    
    for drink, keywords in drinks_keywords.items():
        for keyword in keywords:
            if keyword in text_lower and ("люблю" in text_lower or "нравится" in text_lower or "обожаю" in text_lower):
                if drink not in user_prefs["favorite_drinks"]:
                    user_prefs["favorite_drinks"].append(drink)
                    updated = True
                    logger.info(f"Добавлен любимый напиток для {user_id}: {drink}")
    
    # Еда
    food_keywords = {
        "мясо": ["мясо", "стейк", "шашлык"],
        "рыба": ["рыба", "сельдь", "семга"],
        "салат": ["салат", "овощи"],
        "закуски": ["закуски", "снеки"],
        "сыр": ["сыр", "сырная"],
        "острое": ["острое", "остренькое"]
    }
    
    for food, keywords in food_keywords.items():
        for keyword in keywords:
            if keyword in text_lower and ("люблю" in text_lower or "нравится" in text_lower):
                if food not in user_prefs["favorite_food"]:
                    user_prefs["favorite_food"].append(food)
                    updated = True
                    logger.info(f"Добавлена любимая еда для {user_id}: {food}")
    
    # Не нравится
    if "не люблю" in text_lower or "не нравится" in text_lower or "терпеть не могу" in text_lower:
        # Простое извлечение - можно улучшить
        words = text_lower.split()
        for i, word in enumerate(words):
            if word in ["люблю", "нравится", "могу"] and i + 1 < len(words):
                dislike = words[i + 1]
                if dislike not in user_prefs["dislikes"]:
                    user_prefs["dislikes"].append(dislike)
                    updated = True
    
    if updated:
        user_prefs["last_updated"] = datetime.now().isoformat()
        save_preferences(preferences)
    
    return user_prefs


def get_user_preferences(user_id: int) -> dict:
    """Получает предпочтения пользователя"""
    preferences = load_preferences()
    return preferences.get(str(user_id), {
        "favorite_drinks": [],
        "favorite_food": [],
        "interests": [],
        "dislikes": [],
        "special_dates": []
    })


def get_preferences_text(user_id: int) -> str:
    """Формирует текстовое описание предпочтений для AI"""
    prefs = get_user_preferences(user_id)
    
    if not any([prefs.get("favorite_drinks"), prefs.get("favorite_food"), prefs.get("dislikes")]):
        return ""
    
    parts = ["О предпочтениях гостя:"]
    
    if prefs.get("favorite_drinks"):
        parts.append(f"Любимые напитки: {', '.join(prefs['favorite_drinks'])}")
    
    if prefs.get("favorite_food"):
        parts.append(f"Любимая еда: {', '.join(prefs['favorite_food'])}")
    
    if prefs.get("dislikes"):
        parts.append(f"Не любит: {', '.join(prefs['dislikes'])}")
    
    return ". ".join(parts) + "."
