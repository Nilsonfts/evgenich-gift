# /ai/response_validator.py
"""
Валидация и очистка ответов от AI
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger("evgenich_ai")


def validate_ai_response(response: str, max_length: int = 800) -> Tuple[bool, str]:
    """
    Проверить и очистить ответ от AI
    
    Args:
        response: Сырой ответ от AI
        max_length: Максимальная длина ответа
        
    Returns:
        Tuple[bool, str]: (валиден ли ответ, очищенный ответ)
    """
    # Проверка на пустоту
    if not response or not response.strip():
        logger.warning("AI вернул пустой ответ")
        return False, "Извини, что-то пошло не так 😕 Попробуй переформулировать?"
    
    cleaned_response = response.strip()
    
    # Проверка на минимальную длину
    if len(cleaned_response) < 3:
        logger.warning(f"AI вернул слишком короткий ответ: '{cleaned_response}'")
        return False, "Не совсем понял вопрос 🤔 Спроси по-другому?"
    
    # Проверка на технические ошибки в тексте
    error_patterns = [
        r'\berror\b',
        r'\bexception\b',
        r'\btraceback\b',
        r'\bnull\b',
        r'\bundefined\b',
        r'\bNoneType\b',
        r'\b500\b',
        r'\b503\b',
        r'Internal Server Error',
        r'Bad Gateway'
    ]
    
    for pattern in error_patterns:
        if re.search(pattern, cleaned_response, re.IGNORECASE):
            logger.error(f"Найдена техническая ошибка в ответе AI: {pattern}")
            return False, "Прости, немного заглючил 😅 Спроси ещё раз"
    
    # Проверка на подозрительные паттерны (AI пытается выполнить код или команду)
    suspicious_patterns = [
        r'```',  # Блоки кода
        r'<script',  # JavaScript
        r'eval\(',  # Выполнение кода
        r'exec\(',
        r'__import__',
        r'subprocess',
        r'os\.system'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, cleaned_response, re.IGNORECASE):
            logger.warning(f"Найден подозрительный паттерн в ответе: {pattern}")
            # Удаляем подозрительные части
            cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.IGNORECASE)
    
    # Удаляем лишние пробелы и переносы строк
    cleaned_response = re.sub(r'\s+', ' ', cleaned_response)
    cleaned_response = cleaned_response.strip()
    
    # Проверка на повторения (AI застрял в цикле)
    words = cleaned_response.split()
    if len(words) > 10:
        # Проверяем есть ли одинаковые последовательности из 5+ слов
        for i in range(len(words) - 10):
            chunk = ' '.join(words[i:i+5])
            rest = ' '.join(words[i+5:])
            if chunk in rest:
                logger.warning("Обнаружено повторение в ответе AI")
                # Обрезаем до первого повторения
                cleaned_response = ' '.join(words[:i+5])
                break
    
    # Ограничение длины
    if len(cleaned_response) > max_length:
        logger.info(f"Ответ слишком длинный ({len(cleaned_response)} символов), обрезаем")
        # Обрезаем по последнему предложению в пределах лимита
        truncated = cleaned_response[:max_length]
        
        # Ищем последнюю точку, восклицательный или вопросительный знак
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence_end > max_length * 0.7:  # Если нашли в последних 30%
            cleaned_response = truncated[:last_sentence_end + 1]
        else:
            cleaned_response = truncated.rstrip() + "... 😊"
    
    # Проверка на кавычки (AI иногда возвращает текст в кавычках)
    if cleaned_response.startswith('"') and cleaned_response.endswith('"'):
        cleaned_response = cleaned_response[1:-1].strip()
    
    # Финальная проверка
    if not cleaned_response or len(cleaned_response) < 3:
        logger.error("После очистки ответ стал слишком коротким")
        return False, "Что-то не то получилось 😕 Давай попробуем ещё раз?"
    
    logger.debug(f"Ответ валиден, длина: {len(cleaned_response)} символов")
    return True, cleaned_response


def sanitize_user_input(user_input: str, max_length: int = 1000) -> str:
    """
    Очистить и обезопасить ввод пользователя
    
    Args:
        user_input: Текст от пользователя
        max_length: Максимальная длина
        
    Returns:
        Очищенный текст
    """
    if not user_input:
        return ""
    
    # Обрезаем слишком длинные сообщения
    sanitized = user_input[:max_length]
    
    # Удаляем потенциально опасные последовательности
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick=, onerror=, etc
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    # Нормализуем пробелы
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def check_response_quality(response: str) -> dict:
    """
    Проверить качество ответа AI
    
    Returns:
        dict: Метрики качества
    """
    metrics = {
        "length": len(response),
        "word_count": len(response.split()),
        "has_emoji": bool(re.search(r'[\U0001F300-\U0001F9FF]', response)),
        "has_question": '?' in response,
        "has_greeting": bool(re.search(r'\b(привет|здравствуй|салют)\b', response, re.IGNORECASE)),
        "is_too_short": len(response) < 10,
        "is_too_long": len(response) > 500,
    }
    
    # Оценка качества (0-100)
    score = 100
    
    if metrics["is_too_short"]:
        score -= 30
    if metrics["is_too_long"]:
        score -= 20
    if not metrics["has_emoji"]:
        score -= 15
    
    metrics["quality_score"] = max(0, score)
    
    return metrics
