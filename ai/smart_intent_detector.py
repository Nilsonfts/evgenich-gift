# /ai/smart_intent_detector.py
"""
Умный детектор намерений с поддержкой опечаток
и контекстного анализа
AI System v3.0
"""

import re
import logging
from typing import Tuple, Dict, List, Optional, NamedTuple
from difflib import SequenceMatcher

logger = logging.getLogger("evgenich_ai")


class DetectedIntent(NamedTuple):
    """Результат детекции намерения"""
    name: str
    confidence: float
    entities: Dict
    priority: int


class SmartIntentDetector:
    """Улучшенный детектор намерений с fuzzy matching"""
    
    def __init__(self):
        # Паттерны с вариациями и опечатками
        self.intent_patterns = {
            "booking": {
                "keywords": [
                    "забронировать", "забронир", "бронь", "бронировать",
                    "столик", "резерв", "заказать стол", "место",
                    "забранировать", "зобронировать", "бранировать",  # опечатки
                    "забраниров", "зобраниров", "бронирован",  # ещё опечатки
                    "запись", "записаться", "свободн", "занять",
                ],
                "phrases": [
                    "хочу столик", "можно стол", "есть места", 
                    "свободные столы", "забронить", "брони",
                    "хочу забронировать", "можно забронировать",
                ],
                "priority": 1,
            },
            "address": {
                "keywords": [
                    "адрес", "где", "находитесь", "как пройти", 
                    "как добраться", "дойти", "доехать", "локация",
                    "местоположение", "маршрут", "метро",
                ],
                "phrases": [
                    "где вы", "как вас найти", "где находится",
                    "как к вам", "где бар", "какой адрес",
                ],
                "priority": 2,
            },
            "work_hours": {
                "keywords": [
                    "работаете", "открыты", "закрыты", "часы", 
                    "режим", "график", "время работы", "расписание",
                    "до скольки", "со скольки",
                ],
                "phrases": [
                    "во сколько", "до скольки", "когда открыт",
                    "когда закрыт", "сейчас работает", "сейчас открыт",
                ],
                "priority": 2,
            },
            "karaoke": {
                "keywords": [
                    "караоке", "петь", "спеть", "песни", "микрофон",
                    "karaoke", "карооке", "кароке",  # опечатки
                ],
                "phrases": [
                    "можно попеть", "есть караоке", "поём песни",
                    "хочу петь", "спеть песню",
                ],
                "priority": 3,
            },
            "events": {
                "keywords": [
                    "мероприятия", "события", "вечеринка", "концерт",
                    "выступление", "афиша", "что будет", "программа",
                    "тусовка", "движуха",
                ],
                "phrases": [
                    "что сегодня", "какие планы", "что намечается",
                    "что интересного", "какая программа",
                ],
                "priority": 3,
            },
            "complaint": {
                "keywords": [
                    "жалоба", "плохо", "ужасно", "отвратительно",
                    "недоволен", "разочарован", "обманули", "хамство",
                    "невкусно", "дорого", "долго ждал", "нахамили",
                ],
                "phrases": [
                    "не понравилось", "плохое обслуживание", 
                    "хочу пожаловаться", "верните деньги",
                    "это безобразие", "очень плохо",
                ],
                "priority": 0,  # Высший приоритет - жалобы важны!
            },
            "gratitude": {
                "keywords": [
                    "спасибо", "благодарю", "супер", "класс", 
                    "отлично", "молодец", "круто", "огонь",
                    "топ", "бомба", "зачёт",
                ],
                "phrases": [
                    "было здорово", "всё понравилось", "придём ещё",
                    "очень вкусно", "отличный вечер",
                ],
                "priority": 4,
            },
            "greeting": {
                "keywords": [
                    "привет", "здравствуй", "добрый", "приветик",
                    "хай", "здарова", "йо", "хелло", "ку",
                ],
                "phrases": [
                    "доброе утро", "добрый день", "добрый вечер",
                    "доброй ночи",
                ],
                "priority": 5,
            },
            "price_inquiry": {
                "keywords": [
                    "цена", "стоит", "стоимость", "прайс",
                    "дорого", "дёшево", "бюджет", "чек",
                ],
                "phrases": [
                    "сколько стоит", "какие цены", "средний чек",
                    "во сколько обойдётся",
                ],
                "priority": 3,
            },
        }
        
        # Порог для fuzzy matching (0.0 - 1.0)
        self.fuzzy_threshold = 0.75
    
    def _fuzzy_match(self, word: str, pattern: str) -> float:
        """Проверить похожесть слов (для опечаток)"""
        return SequenceMatcher(None, word.lower(), pattern.lower()).ratio()
    
    def _check_fuzzy_keywords(self, text: str, keywords: List[str]) -> Tuple[bool, float]:
        """Проверить ключевые слова с учётом опечаток"""
        text_lower = text.lower()
        text_words = text_lower.split()
        
        best_score = 0.0
        found = False
        
        for keyword in keywords:
            # Точное вхождение подстроки
            if keyword in text_lower:
                return True, 1.0
        
        # Fuzzy matching для отдельных слов
        for text_word in text_words:
            if len(text_word) < 4:  # Короткие слова пропускаем
                continue
                
            for keyword in keywords:
                if len(keyword) < 4:
                    continue
                    
                score = self._fuzzy_match(text_word, keyword)
                if score > best_score:
                    best_score = score
                if score >= self.fuzzy_threshold:
                    found = True
                    logger.debug(f"Fuzzy match: '{text_word}' ≈ '{keyword}' ({score:.2f})")
        
        return found, best_score
    
    def detect(self, message: str, context: List[Dict] = None) -> DetectedIntent:
        """
        Определить намерение пользователя
        
        Args:
            message: Сообщение пользователя
            context: История разговора (опционально)
            
        Returns:
            DetectedIntent с name, confidence, entities, priority
        """
        message_lower = message.lower().strip()
        
        # Пустое сообщение
        if not message_lower:
            return DetectedIntent("unknown", 0.0, {}, 99)
        
        results = []
        
        for intent_name, config in self.intent_patterns.items():
            keywords = config["keywords"]
            phrases = config.get("phrases", [])
            priority = config["priority"]
            
            # Проверяем фразы (точное совпадение подстроки)
            phrase_match = any(phrase in message_lower for phrase in phrases)
            
            # Проверяем ключевые слова с fuzzy matching
            keyword_match, keyword_score = self._check_fuzzy_keywords(message_lower, keywords)
            
            if phrase_match:
                confidence = 0.95
            elif keyword_match:
                confidence = max(0.7, keyword_score)
            else:
                continue
            
            results.append({
                "intent": intent_name,
                "confidence": confidence,
                "priority": priority,
            })
        
        if not results:
            return DetectedIntent("general", 0.5, {}, 99)
        
        # Сортируем по приоритету (меньше = важнее), потом по confidence (больше = лучше)
        results.sort(key=lambda x: (x["priority"], -x["confidence"]))
        
        best = results[0]
        
        # Извлекаем сущности
        entities = self._extract_entities(message_lower, best["intent"])
        
        logger.info(f"🎯 Намерение: {best['intent']} (conf: {best['confidence']:.2f}), entities: {entities}")
        
        return DetectedIntent(
            name=best["intent"],
            confidence=best["confidence"],
            entities=entities,
            priority=best["priority"]
        )
    
    def _extract_entities(self, message: str, intent: str) -> Dict:
        """Извлечь сущности из сообщения"""
        entities = {}
        
        # === Дата ===
        date_patterns = [
            (r"на завтра", "завтра"),
            (r"на сегодня", "сегодня"),
            (r"на послезавтра", "послезавтра"),
            (r"в пятницу", "пятница"),
            (r"в субботу", "суббота"),
            (r"в воскресенье", "воскресенье"),
            (r"(\d{1,2})[./](\d{1,2})", None),  # 15.01 или 15/01
            (r"(\d{1,2})\s*(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)", None),
        ]
        
        for pattern, value in date_patterns:
            match = re.search(pattern, message)
            if match:
                entities["date"] = value or match.group(0)
                break
        
        # === Время ===
        time_patterns = [
            r"в\s*(\d{1,2})[:\s]?(\d{2})?",
            r"на\s*(\d{1,2})[:\s]?(\d{2})?(?:\s*час)?",
            r"к\s*(\d{1,2})[:\s]?(\d{2})?",
            r"(\d{1,2})[:\s](\d{2})",
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message)
            if match:
                hour = match.group(1)
                minute = match.group(2) or "00"
                # Проверяем что это похоже на время
                if int(hour) <= 24:
                    entities["time"] = f"{hour}:{minute}"
                    break
        
        # === Количество людей ===
        people_patterns = [
            (r"на\s*(\d+)\s*(?:человек|персон|гост|чел)", lambda m: int(m.group(1))),
            (r"(\d+)\s*(?:человек|персон|гост|чел)", lambda m: int(m.group(1))),
            (r"нас\s*(\d+)", lambda m: int(m.group(1))),
            (r"будет\s*(\d+)", lambda m: int(m.group(1))),
            (r"компания\s*(\d+)", lambda m: int(m.group(1))),
            (r"вдвоём|вдвоем", lambda m: 2),
            (r"втроём|втроем", lambda m: 3),
            (r"вчетвером", lambda m: 4),
            (r"впятером", lambda m: 5),
            (r"вшестером", lambda m: 6),
        ]
        
        for pattern, extractor in people_patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    entities["people_count"] = extractor(match)
                    break
                except:
                    pass
        
        # === Бар ===
        if any(word in message for word in ["невский", "невского", "маяковская", "на 53", "53"]):
            entities["bar"] = "nevsky"
        elif any(word in message for word in ["рубинштейна", "рубина", "на 9", " 9"]):
            entities["bar"] = "rubinshteina"
        
        # === Напитки (для меню) ===
        drinks = ["хуба", "пломбир", "фисташк", "клюкв", "облепих", "лимончелло", "таёжн", "кедров"]
        for drink in drinks:
            if drink in message:
                entities["drink_mentioned"] = drink
                break
        
        return entities
    
    def get_supported_intents(self) -> List[str]:
        """Получить список поддерживаемых намерений"""
        return list(self.intent_patterns.keys())


# Глобальный экземпляр
smart_detector = SmartIntentDetector()
