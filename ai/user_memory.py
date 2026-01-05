# /ai/user_memory.py
"""
Модуль долгосрочной памяти о пользователях
Запоминает предпочтения, историю, имя гостя
AI System v3.0
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("evgenich_ai")


class UserMemory:
    """Долгосрочная память о пользователях"""
    
    def __init__(self, storage_file: str = "data/user_memory.json"):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(exist_ok=True)
        self.memory: Dict[int, Dict[str, Any]] = {}
        self._load()
    
    def _load(self):
        """Загрузить память из файла"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем ключи обратно в int
                    self.memory = {int(k): v for k, v in data.items()}
                logger.info(f"📚 Загружена память о {len(self.memory)} пользователях")
            except Exception as e:
                logger.error(f"Ошибка загрузки памяти: {e}")
                self.memory = {}
    
    def _save(self):
        """Сохранить память в файл"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения памяти: {e}")
    
    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Получить профиль пользователя"""
        if user_id not in self.memory:
            self.memory[user_id] = {
                "first_seen": datetime.now().isoformat(),
                "name": None,
                "preferred_bar": None,  # "nevsky" или "rubinshteina"
                "favorite_drinks": [],
                "bookings_count": 0,
                "last_visit": None,
                "notes": [],  # Заметки о госте
                "conversation_style": "formal",  # formal/casual
            }
            self._save()
        return self.memory[user_id]
    
    def remember_name(self, user_id: int, name: str):
        """Запомнить имя пользователя"""
        profile = self.get_user_profile(user_id)
        if name and len(name) > 1:
            # Очищаем имя от лишнего
            clean_name = name.strip().capitalize()
            # Проверяем что это реальное имя, а не глагол
            bad_words = ["хочу", "буду", "могу", "там", "тут", "это", "как", "что", "где"]
            if clean_name.lower() not in bad_words and len(clean_name) > 2:
                profile["name"] = clean_name
                self._save()
                logger.info(f"📝 Запомнил имя для {user_id}: {clean_name}")
    
    def remember_preferred_bar(self, user_id: int, bar: str):
        """Запомнить предпочтительный бар"""
        profile = self.get_user_profile(user_id)
        bar_lower = bar.lower()
        
        if any(word in bar_lower for word in ["невский", "nevsky", "невского", "53", "маяковская"]):
            profile["preferred_bar"] = "nevsky"
            self._save()
            logger.info(f"📍 Запомнил бар для {user_id}: Невский")
        elif any(word in bar_lower for word in ["рубинштейна", "rubinshteina", "рубина", "9"]):
            profile["preferred_bar"] = "rubinshteina"
            self._save()
            logger.info(f"📍 Запомнил бар для {user_id}: Рубинштейна")
    
    def remember_drink(self, user_id: int, drink: str):
        """Запомнить любимый напиток"""
        profile = self.get_user_profile(user_id)
        drink_clean = drink.lower().strip()
        
        if drink_clean and drink_clean not in profile["favorite_drinks"]:
            profile["favorite_drinks"].append(drink_clean)
            # Храним только последние 5
            profile["favorite_drinks"] = profile["favorite_drinks"][-5:]
            self._save()
            logger.info(f"🥃 Запомнил напиток для {user_id}: {drink_clean}")
    
    def increment_bookings(self, user_id: int):
        """Увеличить счётчик бронирований"""
        profile = self.get_user_profile(user_id)
        profile["bookings_count"] += 1
        profile["last_visit"] = datetime.now().isoformat()
        self._save()
        logger.info(f"📊 Бронирований у {user_id}: {profile['bookings_count']}")
    
    def add_note(self, user_id: int, note: str):
        """Добавить заметку о госте"""
        profile = self.get_user_profile(user_id)
        profile["notes"].append({
            "text": note,
            "date": datetime.now().isoformat()
        })
        # Храним последние 10 заметок
        profile["notes"] = profile["notes"][-10:]
        self._save()
    
    def get_personalization_context(self, user_id: int) -> str:
        """Получить контекст для персонализации ответов AI"""
        profile = self.get_user_profile(user_id)
        
        context_parts = []
        
        # Имя
        if profile.get("name"):
            context_parts.append(f"👤 Имя гостя: {profile['name']} (обращайся по имени!)")
        
        # Предпочтительный бар
        if profile.get("preferred_bar"):
            bar_name = "Невский 53" if profile["preferred_bar"] == "nevsky" else "Рубинштейна 9"
            context_parts.append(f"📍 Предпочитает бар: {bar_name}")
        
        # Любимые напитки
        if profile.get("favorite_drinks"):
            drinks = ", ".join(profile["favorite_drinks"][-3:])
            context_parts.append(f"🥃 Любимые напитки: {drinks}")
        
        # Статус гостя
        bookings = profile.get("bookings_count", 0)
        if bookings == 0:
            context_parts.append("🆕 Статус: новый гость (будь особенно гостеприимным!)")
        elif bookings < 3:
            context_parts.append(f"📊 Статус: был {bookings} раз (уже знакомый!)")
        elif bookings < 10:
            context_parts.append(f"⭐ Статус: постоянный гость ({bookings} визитов)")
        else:
            context_parts.append(f"👑 Статус: VIP-гость ({bookings} визитов!)")
        
        # Последний визит
        if profile.get("last_visit"):
            try:
                last = datetime.fromisoformat(profile["last_visit"])
                days_ago = (datetime.now() - last).days
                if days_ago < 7:
                    context_parts.append("🕐 Был недавно")
                elif days_ago < 30:
                    context_parts.append(f"🕐 Был {days_ago} дней назад")
                else:
                    context_parts.append("🕐 Давно не заходил (поприветствуй теплее!)")
            except:
                pass
        
        if context_parts:
            return "📋 ИНФОРМАЦИЯ О ГОСТЕ:\n" + "\n".join(context_parts)
        return ""
    
    def extract_info_from_message(self, user_id: int, message: str):
        """Извлечь и запомнить информацию из сообщения"""
        message_lower = message.lower()
        
        # === Извлекаем имя ===
        name_patterns = [
            r"меня зовут (\w+)",
            r"я (\w+)[,\.\!]",
            r"зови меня (\w+)",
            r"моё? имя (\w+)",
            r"это (\w+) пишет",
            r"привет,?\s*я (\w+)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1).capitalize()
                self.remember_name(user_id, name)
                break
        
        # === Извлекаем предпочтения по бару ===
        if any(word in message_lower for word in ["невский", "невского", "маяковская", "на 53"]):
            self.remember_preferred_bar(user_id, "nevsky")
        elif any(word in message_lower for word in ["рубинштейна", "рубина", "на 9"]):
            self.remember_preferred_bar(user_id, "rubinshteina")
        
        # === Извлекаем любимые напитки ===
        drinks_map = {
            "хуба": "Хуба-Буба",
            "пломбир": "Фисташковый пломбир",
            "фисташк": "Фисташковый пломбир",
            "клюкв": "Клюквенная",
            "облепих": "Облепиховая",
            "лимончелло": "Лимончелло",
            "таёжн": "Таёжная",
            "таежн": "Таёжная",
            "кедров": "Кедровая",
            "хрен": "Хреновуха",
        }
        
        for keyword, drink_name in drinks_map.items():
            if keyword in message_lower:
                self.remember_drink(user_id, drink_name)
    
    def get_greeting_for_user(self, user_id: int) -> str:
        """Получить персонализированное приветствие"""
        profile = self.get_user_profile(user_id)
        
        if profile.get("name"):
            return f"Привет, {profile['name']}! 😊"
        else:
            return "Привет, товарищ! 😊"
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику по памяти"""
        total = len(self.memory)
        with_names = sum(1 for u in self.memory.values() if u.get("name"))
        with_bars = sum(1 for u in self.memory.values() if u.get("preferred_bar"))
        with_drinks = sum(1 for u in self.memory.values() if u.get("favorite_drinks"))
        vip = sum(1 for u in self.memory.values() if u.get("bookings_count", 0) >= 10)
        
        return {
            "total_users": total,
            "with_names": with_names,
            "with_preferred_bar": with_bars,
            "with_favorite_drinks": with_drinks,
            "vip_guests": vip,
        }


# Глобальный экземпляр
user_memory = UserMemory()
