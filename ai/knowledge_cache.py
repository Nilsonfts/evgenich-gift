# /ai/knowledge_cache.py
"""
Кеширование базы знаний и других данных для повышения производительности
"""
import logging
import time
from pathlib import Path
from typing import Optional, Any, Dict
from functools import wraps

logger = logging.getLogger("evgenich_ai")


class SimpleCache:
    """Простой кеш с TTL (time-to-live)"""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: Время жизни кеша в секундах (по умолчанию 5 минут)
        """
        self.ttl = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Проверяем не истекло ли время жизни
        if time.time() - entry["timestamp"] > self.ttl:
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit для ключа: {key}")
        return entry["value"]
    
    def set(self, key: str, value: Any) -> None:
        """Сохранить значение в кеш"""
        self._cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        logger.debug(f"Cache set для ключа: {key}")
    
    def clear(self, key: Optional[str] = None) -> None:
        """Очистить кеш (весь или по ключу)"""
        if key:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache cleared для ключа: {key}")
        else:
            self._cache.clear()
            logger.debug("Cache полностью очищен")
    
    def get_stats(self) -> dict:
        """Получить статистику кеша"""
        current_time = time.time()
        active_entries = sum(
            1 for entry in self._cache.values()
            if current_time - entry["timestamp"] <= self.ttl
        )
        
        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "ttl_seconds": self.ttl
        }


# Глобальные кеши для разных типов данных
knowledge_base_cache = SimpleCache(ttl_seconds=300)  # 5 минут
user_data_cache = SimpleCache(ttl_seconds=180)  # 3 минуты
bar_context_cache = SimpleCache(ttl_seconds=600)  # 10 минут


def cached_knowledge_base() -> str:
    """
    Получить базу знаний с кешированием
    
    Returns:
        Текст базы знаний
    """
    cache_key = "knowledge_base_text"
    
    # Пробуем получить из кеша
    cached_value = knowledge_base_cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    
    # Загружаем из модуля
    try:
        from ai.knowledge_base import KNOWLEDGE_BASE_TEXT
        knowledge_base_cache.set(cache_key, KNOWLEDGE_BASE_TEXT)
        logger.info("База знаний загружена и закеширована")
        return KNOWLEDGE_BASE_TEXT
    except Exception as e:
        logger.error(f"Ошибка загрузки базы знаний: {e}")
        return ""


def cache_with_ttl(cache_instance: SimpleCache, key_prefix: str = ""):
    """
    Декоратор для кеширования результатов функций
    
    Args:
        cache_instance: Экземпляр кеша
        key_prefix: Префикс для ключа кеша
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Формируем ключ кеша из имени функции и аргументов
            cache_key = f"{key_prefix}{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Пробуем получить из кеша
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Вычисляем значение
            result = func(*args, **kwargs)
            
            # Сохраняем в кеш
            cache_instance.set(cache_key, result)
            
            return result
        return wrapper
    return decorator


def get_cache_stats() -> dict:
    """Получить статистику всех кешей"""
    return {
        "knowledge_base": knowledge_base_cache.get_stats(),
        "user_data": user_data_cache.get_stats(),
        "bar_context": bar_context_cache.get_stats()
    }


def clear_all_caches() -> None:
    """Очистить все кеши"""
    knowledge_base_cache.clear()
    user_data_cache.clear()
    bar_context_cache.clear()
    logger.info("Все кеши очищены")
