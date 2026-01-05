# /ai/retry_handler.py
"""
Обработка retry логики для OpenAI API с exponential backoff
"""
import logging
import time
from typing import Callable, Any
from openai import OpenAIError, RateLimitError, APIError, APIConnectionError

logger = logging.getLogger("evgenich_ai")


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    fallback_response: str = None
) -> Any:
    """
    Выполнить функцию с retry логикой и exponential backoff
    
    Args:
        func: Функция для выполнения
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка в секундах
        backoff_factor: Множитель для увеличения задержки
        fallback_response: Ответ при исчерпании попыток
    
    Returns:
        Результат выполнения функции или fallback_response
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            return func()
            
        except RateLimitError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Rate limit hit (попытка {attempt + 1}/{max_retries}), "
                    f"ожидание {delay:.1f}s... Ошибка: {e}"
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"Rate limit после {max_retries} попыток")
                if fallback_response:
                    return fallback_response
                raise
                
        except APIConnectionError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Проблема с подключением (попытка {attempt + 1}/{max_retries}), "
                    f"ожидание {delay:.1f}s... Ошибка: {e}"
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"Проблема с подключением после {max_retries} попыток")
                if fallback_response:
                    return fallback_response
                raise
                
        except APIError as e:
            if attempt < max_retries - 1 and e.status_code >= 500:
                # Повторяем только при серверных ошибках (5xx)
                logger.warning(
                    f"Серверная ошибка API (попытка {attempt + 1}/{max_retries}), "
                    f"ожидание {delay:.1f}s... Код: {e.status_code}"
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"API ошибка: {e}")
                if fallback_response:
                    return fallback_response
                raise
                
        except OpenAIError as e:
            logger.error(f"Неожиданная ошибка OpenAI: {e}")
            if fallback_response:
                return fallback_response
            raise
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при вызове API: {e}", exc_info=True)
            if fallback_response:
                return fallback_response
            raise
    
    # Не должны сюда попасть, но на всякий случай
    if fallback_response:
        return fallback_response
    raise Exception(f"Не удалось выполнить запрос после {max_retries} попыток")


def get_user_friendly_error(exception: Exception) -> str:
    """
    Получить дружелюбное сообщение об ошибке для пользователя
    
    Args:
        exception: Исключение которое произошло
        
    Returns:
        Дружелюбное сообщение для пользователя
    """
    if isinstance(exception, RateLimitError):
        return "Прости, товарищ! 😅 Сейчас слишком много народу спрашивает. Попробуй через минутку!"
    
    elif isinstance(exception, APIConnectionError):
        return "Что-то с интернетом приключилось 😕 Попробуй ещё раз через секунду"
    
    elif isinstance(exception, APIError):
        return "Связь с моим мозгом пропала 🤖 Давай попробуем снова?"
    
    elif isinstance(exception, OpenAIError):
        return "Что-то пошло не так с моим ассистентом 😅 Попробуй переформулировать вопрос"
    
    else:
        return "Ой, что-то глюкнуло 😕 Попробуй ещё раз, а?"
