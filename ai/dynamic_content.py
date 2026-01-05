# /ai/dynamic_content.py
"""
Модуль для динамического контента
Акции, мероприятия, специальные предложения
AI System v3.0
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger("evgenich_ai")


class DynamicContent:
    """Управление динамическим контентом для AI"""
    
    def __init__(self, storage_file: str = "data/dynamic_content.json"):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(exist_ok=True)
        self.content = {
            "promotions": [],  # Акции
            "events": [],  # Мероприятия
            "specials": [],  # Специальные предложения
            "announcements": [],  # Объявления
        }
        self._load()
    
    def _load(self):
        """Загрузить контент"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.content = json.load(f)
                logger.info(f"📢 Загружен динамический контент: {len(self.content.get('promotions', []))} акций, {len(self.content.get('events', []))} мероприятий")
            except Exception as e:
                logger.error(f"Ошибка загрузки dynamic_content: {e}")
        else:
            # Создаём файл с начальными данными
            self._save()
    
    def _save(self):
        """Сохранить контент"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.content, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения dynamic_content: {e}")
    
    def _generate_id(self, category: str) -> int:
        """Генерация уникального ID"""
        items = self.content.get(category, [])
        if not items:
            return 1
        return max(item.get("id", 0) for item in items) + 1
    
    def add_promotion(self, title: str, description: str, 
                      valid_until: str = None, bar: str = "both") -> Dict:
        """
        Добавить акцию
        
        Args:
            title: Название акции
            description: Описание
            valid_until: Дата окончания (YYYY-MM-DD) или None для бессрочной
            bar: Бар ("nevsky", "rubinshteina", "both")
        """
        promotion = {
            "id": self._generate_id("promotions"),
            "title": title,
            "description": description,
            "valid_until": valid_until,
            "bar": bar,
            "created_at": datetime.now().isoformat(),
            "active": True,
        }
        self.content["promotions"].append(promotion)
        self._save()
        logger.info(f"🎁 Добавлена акция #{promotion['id']}: {title}")
        return promotion
    
    def add_event(self, title: str, description: str, 
                  date: str, time: str, bar: str = "both") -> Dict:
        """
        Добавить мероприятие
        
        Args:
            title: Название мероприятия
            description: Описание
            date: Дата (YYYY-MM-DD)
            time: Время (HH:MM)
            bar: Бар
        """
        event = {
            "id": self._generate_id("events"),
            "title": title,
            "description": description,
            "date": date,
            "time": time,
            "bar": bar,
            "created_at": datetime.now().isoformat(),
            "active": True,
        }
        self.content["events"].append(event)
        self._save()
        logger.info(f"🎉 Добавлено мероприятие #{event['id']}: {title} на {date}")
        return event
    
    def add_announcement(self, text: str, expires_at: str = None) -> Dict:
        """Добавить объявление"""
        announcement = {
            "id": self._generate_id("announcements"),
            "text": text,
            "expires_at": expires_at,
            "created_at": datetime.now().isoformat(),
            "active": True,
        }
        self.content["announcements"].append(announcement)
        self._save()
        return announcement
    
    def get_active_promotions(self, bar: str = None) -> List[Dict]:
        """
        Получить активные акции
        
        Args:
            bar: Фильтр по бару (None = все)
        """
        now = datetime.now()
        active = []
        
        for promo in self.content.get("promotions", []):
            if not promo.get("active"):
                continue
            
            # Проверяем срок действия
            if promo.get("valid_until"):
                try:
                    valid = datetime.fromisoformat(promo["valid_until"])
                    if now.date() > valid.date():
                        continue
                except:
                    pass
            
            # Фильтр по бару
            if bar and promo.get("bar") not in [bar, "both"]:
                continue
            
            active.append(promo)
        
        return active
    
    def get_upcoming_events(self, days: int = 7, bar: str = None) -> List[Dict]:
        """
        Получить ближайшие мероприятия
        
        Args:
            days: На сколько дней вперёд
            bar: Фильтр по бару
        """
        now = datetime.now()
        upcoming = []
        
        for event in self.content.get("events", []):
            if not event.get("active"):
                continue
            
            try:
                event_date = datetime.fromisoformat(event["date"])
                # Мероприятие уже прошло
                if event_date.date() < now.date():
                    continue
                # Мероприятие слишком далеко
                if event_date > now + timedelta(days=days):
                    continue
            except:
                continue
            
            # Фильтр по бару
            if bar and event.get("bar") not in [bar, "both"]:
                continue
            
            upcoming.append(event)
        
        return sorted(upcoming, key=lambda x: x["date"])
    
    def get_active_announcements(self) -> List[Dict]:
        """Получить активные объявления"""
        now = datetime.now()
        active = []
        
        for ann in self.content.get("announcements", []):
            if not ann.get("active"):
                continue
            
            if ann.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(ann["expires_at"])
                    if now > expires:
                        continue
                except:
                    pass
            
            active.append(ann)
        
        return active
    
    def get_context_for_ai(self, bar: str = None) -> str:
        """
        Получить контекст для AI промпта
        
        Returns:
            Строка с актуальными акциями и мероприятиями для AI
        """
        parts = []
        
        # Акции
        promotions = self.get_active_promotions(bar)
        if promotions:
            promo_texts = []
            for p in promotions[:3]:  # Максимум 3
                promo_texts.append(f"• {p['title']}: {p['description']}")
            parts.append("🎁 АКТУАЛЬНЫЕ АКЦИИ:\n" + "\n".join(promo_texts))
        
        # Мероприятия
        events = self.get_upcoming_events(7, bar)
        if events:
            event_texts = []
            for e in events[:3]:  # Максимум 3
                # Форматируем дату красиво
                try:
                    date_obj = datetime.fromisoformat(e["date"])
                    date_str = date_obj.strftime("%d.%m")
                except:
                    date_str = e["date"]
                event_texts.append(f"• {date_str} в {e['time']}: {e['title']}")
            parts.append("🎉 БЛИЖАЙШИЕ МЕРОПРИЯТИЯ:\n" + "\n".join(event_texts))
        
        # Объявления
        announcements = self.get_active_announcements()
        if announcements:
            ann_texts = [a["text"] for a in announcements[:2]]
            parts.append("📢 ОБЪЯВЛЕНИЯ:\n" + "\n".join(ann_texts))
        
        if parts:
            return "\n\n".join(parts) + "\n\nМожешь упомянуть актуальные акции/мероприятия если уместно!"
        return ""
    
    def deactivate_promotion(self, promo_id: int) -> bool:
        """Деактивировать акцию"""
        for promo in self.content.get("promotions", []):
            if promo["id"] == promo_id:
                promo["active"] = False
                self._save()
                logger.info(f"🗑️ Деактивирована акция #{promo_id}")
                return True
        return False
    
    def deactivate_event(self, event_id: int) -> bool:
        """Деактивировать мероприятие"""
        for event in self.content.get("events", []):
            if event["id"] == event_id:
                event["active"] = False
                self._save()
                logger.info(f"🗑️ Деактивировано мероприятие #{event_id}")
                return True
        return False
    
    def deactivate_announcement(self, ann_id: int) -> bool:
        """Деактивировать объявление"""
        for ann in self.content.get("announcements", []):
            if ann["id"] == ann_id:
                ann["active"] = False
                self._save()
                return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        return {
            "active_promotions": len(self.get_active_promotions()),
            "upcoming_events": len(self.get_upcoming_events()),
            "active_announcements": len(self.get_active_announcements()),
            "total_promotions": len(self.content.get("promotions", [])),
            "total_events": len(self.content.get("events", [])),
        }
    
    def cleanup_expired(self) -> int:
        """Очистить просроченный контент"""
        now = datetime.now()
        cleaned = 0
        
        # Деактивируем просроченные акции
        for promo in self.content.get("promotions", []):
            if promo.get("active") and promo.get("valid_until"):
                try:
                    valid = datetime.fromisoformat(promo["valid_until"])
                    if now.date() > valid.date():
                        promo["active"] = False
                        cleaned += 1
                except:
                    pass
        
        # Деактивируем прошедшие мероприятия
        for event in self.content.get("events", []):
            if event.get("active"):
                try:
                    event_date = datetime.fromisoformat(event["date"])
                    if event_date.date() < now.date():
                        event["active"] = False
                        cleaned += 1
                except:
                    pass
        
        if cleaned > 0:
            self._save()
            logger.info(f"🧹 Очищено {cleaned} просроченных записей")
        
        return cleaned


# Глобальный экземпляр
dynamic_content = DynamicContent()
