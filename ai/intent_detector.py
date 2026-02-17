# /ai/intent_detector.py
"""
Улучшенный детектор намерений пользователя
Определяет что хочет пользователь для более точной обработки
"""
import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("evgenich_ai")


@dataclass
class Intent:
    """Результат распознавания намерения"""
    name: str  # Название намерения
    confidence: float  # Уверенность (0.0 - 1.0)
    entities: Dict[str, any]  # Извлечённые сущности (даты, номера и т.д.)


class IntentDetector:
    """
    Детектор намерений пользователя
    
    Определяет что хочет сделать пользователь:
    - забронировать столик
    - узнать меню/цены
    - узнать адрес/время работы
    - пожаловаться
    - просто поболтать
    """
    
    # Паттерны для разных намерений
    INTENT_PATTERNS = {
        "booking": {
            "keywords": [
                r"\bзабронир",
                r"\bбронь",
                r"\bрезерв",
                r"\bстолик",
                r"\bстол",
                r"\bместо",
                r"\bзабрать\s+стол",
            ],
            "weight": 1.0
        },
        "address": {
            "keywords": [
                r"\bадрес",
                r"\bгде\s+находит",
                r"\bкак\s+пройти",
                r"\bкак\s+добраться",
                r"\bгде\s+вы",
                r"\bгде\s+бар",
                r"\bневский",
                r"\bрубинштейн",
            ],
            "weight": 0.95
        },
        "work_hours": {
            "keywords": [
                r"\bкогда\s+работа",
                r"\bрежим\s+работы",
                r"\bчасы\s+работы",
                r"\bдо\s+скольк",
                r"\bоткрыт",
                r"\bзакрыт",
                r"\bсейчас\s+открыт",
                r"\bсейчас\s+работа",
            ],
            "weight": 0.9
        },
        "complaint": {
            "keywords": [
                r"\bжалоб",
                r"\bплохо",
                r"\bужасно",
                r"\bотврат",
                r"\bобслужива",
                r"\bне\s+понравил",
                r"\bпроблем",
                r"\bнедоволен",
                r"\bразочаров",
            ],
            "weight": 0.85
        },
        "price_inquiry": {
            "keywords": [
                r"\bсколько\s+стоит",
                r"\bцена",
                r"\bцены",
                r"\bстоимость",
                r"\bсредний\s+чек",
            ],
            "weight": 0.9
        },
        "karaoke": {
            "keywords": [
                r"\bкараоке",
                r"\bпеть",
                r"\bпесн",
                r"\bмикрофон",
                r"\bсцен",
            ],
            "weight": 0.85
        },
        "event": {
            "keywords": [
                r"\bмероприятие",
                r"\bпраздник",
                r"\bдень\s+рождени",
                r"\bкорпоратив",
                r"\bбанкет",
                r"\bвыкуп\s+зала",
            ],
            "weight": 0.8
        },
        "payment": {
            "keywords": [
                r"\bоплат",
                r"\bкарт",
                r"\bналичн",
                r"\bсбп",
                r"\bчаевые",
            ],
            "weight": 0.75
        },
        "greeting": {
            "keywords": [
                r"^\s*(привет|здравствуй|салют|йо|хай|hi|hello)\s*[!?.]?\s*$",
                r"^\s*добр(ое|ый|ого)\s+(утро|день|вечер)",
            ],
            "weight": 0.95
        },
        "gratitude": {
            "keywords": [
                r"\bспасибо",
                r"\bблагодар",
                r"\bthank",
                r"\bмерси",
                r"\bпризнателен",
            ],
            "weight": 0.9
        },
        "general": {
            "keywords": [],  # По умолчанию
            "weight": 0.3
        }
    }
    
    def detect(self, text: str) -> Intent:
        """
        Определить намерение пользователя
        
        Args:
            text: Текст сообщения от пользователя
            
        Returns:
            Intent с названием, уверенностью и извлечёнными сущностями
        """
        if not text or not text.strip():
            return Intent("general", 0.5, {})
        
        text_lower = text.lower().strip()
        
        # Счётчики для каждого намерения
        scores = {}
        
        for intent_name, intent_config in self.INTENT_PATTERNS.items():
            score = 0.0
            matches = 0
            
            for pattern in intent_config["keywords"]:
                if re.search(pattern, text_lower):
                    matches += 1
                    score += intent_config["weight"]
            
            # Нормализуем score
            if matches > 0:
                # Бонус за множественные совпадения
                score = min(1.0, score * (1 + matches * 0.1))
            
            scores[intent_name] = score
        
        # Находим намерение с максимальным score
        if not scores or max(scores.values()) < 0.3:
            detected_intent = "general"
            confidence = 0.3
        else:
            detected_intent = max(scores, key=scores.get)
            confidence = scores[detected_intent]
        
        # Извлекаем сущности
        entities = self._extract_entities(text_lower, detected_intent)
        
        logger.debug(
            f"Детектировано намерение: {detected_intent} "
            f"(уверенность: {confidence:.2f}, сущности: {entities})"
        )
        
        return Intent(detected_intent, confidence, entities)
    
    def _extract_entities(self, text: str, intent: str) -> Dict[str, any]:
        """
        Извлечь сущности из текста в зависимости от намерения
        
        Args:
            text: Текст сообщения (в нижнем регистре)
            intent: Определённое намерение
            
        Returns:
            Словарь с извлечёнными сущностями
        """
        entities = {}
        
        # Извлечение даты и времени для бронирования
        if intent == "booking":
            # Ищем дату
            date_patterns = [
                r"\b(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)",
                r"\b(\d{1,2})\.(\d{1,2})",  # 10.01
                r"\b(завтра|послезавтра|сегодня)",
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    entities["date"] = match.group(0)
                    break
            
            # Ищем время
            time_match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
            if time_match:
                entities["time"] = time_match.group(0)
            else:
                # Ищем время в других форматах
                time_match = re.search(r"\b(\d{1,2})\s+час", text)
                if time_match:
                    entities["time"] = f"{time_match.group(1)}:00"
            
            # Ищем количество человек
            people_match = re.search(r"\b(\d+)\s*(человек|чел|людей|персон)", text)
            if people_match:
                entities["people_count"] = int(people_match.group(1))
        
        # Извлечение адреса
        if intent == "address":
            if "невский" in text or "невск" in text:
                entities["bar_location"] = "nevsky"
            if "рубинштейн" in text or "рубин" in text:
                entities["bar_location"] = "rubinstein"
        

        return entities
    
    def is_question(self, text: str) -> bool:
        """Проверить является ли текст вопросом"""
        text = text.strip()
        
        # Заканчивается на вопросительный знак
        if text.endswith("?"):
            return True
        
        # Начинается с вопросительного слова
        question_words = [
            r"^\s*(как|где|когда|что|почему|зачем|какой|какая|сколько|куда|откуда)",
            r"^\s*(можно|есть|будет|работает)",
        ]
        
        for pattern in question_words:
            if re.search(pattern, text.lower()):
                return True
        
        return False
    
    def get_intent_priority(self, intent_name: str) -> int:
        """
        Получить приоритет намерения для обработки
        
        Returns:
            Приоритет (чем меньше число, тем выше приоритет)
        """
        priorities = {
            "complaint": 1,      # Жалобы - самый высокий приоритет
            "booking": 2,        # Бронирование
            "payment": 3,        # Оплата
            "event": 4,          # События
            "address": 5,        # Адрес
            "work_hours": 6,     # Часы работы
            "price_inquiry": 8,  # Цены
            "karaoke": 9,        # Караоке
            "greeting": 10,      # Приветствие
            "gratitude": 11,     # Благодарность
            "general": 12        # Общие вопросы
        }
        
        return priorities.get(intent_name, 99)


# Глобальный экземпляр
intent_detector = IntentDetector()
