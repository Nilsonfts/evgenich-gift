# /ai/conversation_context.py
"""
Управление контекстом разговоров пользователей с AI
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger("evgenich_ai")


class ConversationContext:
    """
    Управление историей диалогов с пользователями
    
    Хранит последние N сообщений для каждого пользователя
    и автоматически очищает старые диалоги
    """
    
    def __init__(self, max_messages: int = 5, ttl_minutes: int = 30):
        """
        Args:
            max_messages: Максимальное количество сообщений на пользователя (пары user/assistant)
            ttl_minutes: Время жизни контекста в минутах
        """
        self.max_messages = max_messages
        self.ttl = timedelta(minutes=ttl_minutes)
        self.contexts: Dict[int, List[Dict[str, str]]] = defaultdict(list)
        self.timestamps: Dict[int, datetime] = {}
    
    def add_message(self, user_id: int, role: str, content: str) -> None:
        """
        Добавить сообщение в контекст пользователя
        
        Args:
            user_id: ID пользователя
            role: Роль ('user' или 'assistant')
            content: Текст сообщения
        """
        now = datetime.now()
        
        # Проверяем не истёк ли контекст
        if user_id in self.timestamps:
            if now - self.timestamps[user_id] > self.ttl:
                logger.info(f"Контекст истёк для пользователя {user_id}, очищаем")
                self.contexts[user_id].clear()
        
        # Обновляем время последнего сообщения
        self.timestamps[user_id] = now
        
        # Добавляем сообщение
        self.contexts[user_id].append({
            "role": role,
            "content": content
        })
        
        # Ограничиваем размер контекста (пары user-assistant)
        max_total_messages = self.max_messages * 2  # user + assistant
        if len(self.contexts[user_id]) > max_total_messages:
            # Удаляем самые старые сообщения (по парам)
            self.contexts[user_id] = self.contexts[user_id][-max_total_messages:]
            logger.debug(f"Контекст обрезан для пользователя {user_id}")
        
        logger.debug(
            f"Добавлено сообщение для пользователя {user_id}, "
            f"роль: {role}, всего сообщений: {len(self.contexts[user_id])}"
        )
    
    def get_context(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получить контекст диалога для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений в формате [{"role": "user", "content": "..."}, ...]
        """
        # Проверяем актуальность контекста
        if user_id in self.timestamps:
            if datetime.now() - self.timestamps[user_id] > self.ttl:
                logger.info(f"Контекст истёк для пользователя {user_id}")
                self.clear_context(user_id)
                return []
        
        return self.contexts.get(user_id, []).copy()
    
    def clear_context(self, user_id: int) -> None:
        """
        Очистить контекст для конкретного пользователя
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self.contexts:
            del self.contexts[user_id]
        if user_id in self.timestamps:
            del self.timestamps[user_id]
        logger.info(f"Контекст очищен для пользователя {user_id}")
    
    def clear_all(self) -> None:
        """Очистить все контексты"""
        self.contexts.clear()
        self.timestamps.clear()
        logger.info("Все контексты очищены")
    
    def get_context_age(self, user_id: int) -> Optional[timedelta]:
        """
        Получить возраст контекста (время с последнего сообщения)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            timedelta или None если контекста нет
        """
        if user_id not in self.timestamps:
            return None
        return datetime.now() - self.timestamps[user_id]
    
    def has_context(self, user_id: int) -> bool:
        """
        Проверить есть ли активный контекст у пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если есть активный контекст
        """
        if user_id not in self.contexts or not self.contexts[user_id]:
            return False
        
        # Проверяем не истёк ли
        if user_id in self.timestamps:
            if datetime.now() - self.timestamps[user_id] > self.ttl:
                return False
        
        return True
    
    def get_stats(self) -> dict:
        """
        Получить статистику по всем контекстам
        
        Returns:
            dict со статистикой
        """
        now = datetime.now()
        active_contexts = 0
        total_messages = 0
        
        for user_id, messages in self.contexts.items():
            if user_id in self.timestamps:
                age = now - self.timestamps[user_id]
                if age <= self.ttl:
                    active_contexts += 1
                    total_messages += len(messages)
        
        return {
            "total_users": len(self.contexts),
            "active_contexts": active_contexts,
            "total_messages": total_messages,
            "avg_messages_per_user": total_messages / active_contexts if active_contexts > 0 else 0,
            "ttl_minutes": self.ttl.total_seconds() / 60,
            "max_messages": self.max_messages
        }
    
    def cleanup_expired(self) -> int:
        """
        Очистить истекшие контексты
        
        Returns:
            Количество очищенных контекстов
        """
        now = datetime.now()
        expired_users = []
        
        for user_id, timestamp in self.timestamps.items():
            if now - timestamp > self.ttl:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.clear_context(user_id)
        
        if expired_users:
            logger.info(f"Очищено {len(expired_users)} истекших контекстов")
        
        return len(expired_users)


# Глобальный экземпляр для всего приложения
conversation_context = ConversationContext(max_messages=5, ttl_minutes=30)
