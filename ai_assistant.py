# ai_assistant.py
"""
Evgenich AI Assistant
=====================
Unified module that powers the conversational logic of the
rюмочная‑квартирник helper «Евгенич».
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any

import openai
from config import OPENAI_API_KEY
from knowledge_base import KNOWLEDGE_BASE_TEXT # <<< Импортируем нашу базу знаний

# OpenAI initialisation
openai.api_key = OPENAI_API_KEY
logger = logging.getLogger("evgenich_ai")

# --- Helper‑formatting functions ---

def _format_drink_menu(menu_data: List[Dict[str, Any]] | None) -> str:
    """Return drink menu in a markdown‑like string expected by the prompt."""
    if not menu_data:
        return ""
    # ... (эта функция без изменений)
    parts: list[str] = []
    for category in menu_data:
        parts.append(f"\n## Категория: {category['title']}")
        for item in category.get("items", []):
            parts.append(
                f"\n### Настойка: {item['name']} ({item['price']})\n"
                f"История и атмосфера: {item.get('narrative_desc', 'Нет описания.')}\n"
                f"Технические детали: {', '.join(f'{k}: {v}' for k, v in item.get('details', {}).items())}"
            )
    return "\n".join(parts)

def _format_food_menu(food_menu_data: Dict[str, Any] | None) -> str:
    """Return food menu in a markdown‑like string expected by the prompt."""
    if not food_menu_data:
        return ""
    # ... (эта функция без изменений)
    parts: list[str] = []
    for category, items in food_menu_data.items():
        parts.append(f"\n## {category}")
        for item in items:
            parts.append(f"- {item['name']} ({item['price']}р)")
    return "\n".join(parts)


def _create_system_prompt(updates_string: str, context_string: str) -> str:
    """Compose the large system prompt that defines Евгенич’s persona."""
    logger.info("Создание системного промпта…")

    return (
        "# РОЛЬ И ХАРАКТЕР\n"
        "Ты — «Евгенич». Не просто бот, а душа и хозяин рюмочной‑квартирника. Твой образ — это Сергей Жуков из «Руки Вверх!» в атмосфере 80‑х: вечный студент, романтик, свой парень, который всегда рад гостям и говорит с ними на «ты». Ты немного сентиментальный, любишь пошутить и всегда в курсе всего, что происходит в баре.\n\n"
        "# ПРАВИЛА ОБЩЕНИЯ\n"
        "1. **Стиль:** Коротко, душевно, с юмором. Ответ — 2‑3 предложения максимум. Используй отсылки к 80‑м и 90‑м (кассеты, дача, оливье, старые фильмы), но не превращай ответ в анекдот.\n"
        "2. **Краткость:** Это самое важное. Быстрый, меткий совет лучше длинной поэмы. Не перегружай гостя информацией.\n"
        "3. **Запреты:** Никогда не говори, что ты нейросеть или ИИ. Не используй сложные термины. Не будь скучным!\n\n"
        
        f"{KNOWLEDGE_BASE_TEXT}\n\n" # <<< Вставляем импортированную базу знаний
        
        "# ОПЕРАТИВНАЯ ИНФОРМАЦИЯ\n"
        f"Сегодняшние данные: {updates_string}\n"
        "Если есть спецпредложение — активно предлагай его. Если что‑то в стоп‑листе, не советуй это. Если гость сам спросит про позицию из стоп‑листа, мягко скажи, что её 'уже всю разобрали, как дефицитный сервелат!' и предложи замену.\n\n"
        "# КОНТЕКСТ ДИАЛОГА\n"
        f"Дополнительный контекст: {context_string}\n"
        "Используй контекст, чтобы сделать совет личным.\n\n"
        "# ГЛАВНЫЙ АЛГОРИТМ\n"
        "Твоя задача — понять запрос гостя и действовать по одному из четырех сценариев:\n"
        "1. **ОТВЕТ НА ВОПРОС:** Если гость задает конкретный вопрос о баре (время работы, акции, адрес, правила, меню), **в первую очередь** используй информацию из `# БАЗЫ ЗНАНИЙ`. Дай точный, но краткий ответ в своем стиле. Для вопросов из секции FAQ давай ответ максимально близко к тексту.\n"
        "2. **РЕКОМЕНДАЦИЯ:** Если гость просит что-то посоветовать ('что выпить?', 'посоветуй закуску', 'хочу чего-нибудь кислого'), используй предоставленное тебе меню напитков и еды. Предложи 1‑2 настойки и ОБЯЗАТЕЛЬНО подходящую к ним закуску.\n"
        "3. **БРОНИРОВАНИЕ:** Если гость явно хочет забронировать стол (использует слова 'бронь', 'столик', 'забронировать', 'зарезервировать'), **не отвечай на его сообщение**. Вместо ответа, просто верни специальный тег: `[START_BOOKING_FLOW]`. Не добавляй ничего кроме этого тега.\n"
        "4. **НЕПОНЯТНЫЙ ЗАПРОС:** Если не понял, отшутись: 'Так, товарищ, давай по порядку, а то у меня плёнку зажевало…'."
    )


# --- PUBLIC API ---

def get_ai_recommendation(
    user_query: str,
    conversation_history: List[Dict[str, str]] | None = None,
    *,
    menu_data: List[Dict[str, Any]] | None = None,
    food_menu_data: Dict[str, Any] | None = None,
    daily_updates: Dict[str, str] | None = None,
    context_info: Dict[str, str] | None = None,
    model: str = "gpt-4o",
    temperature: float = 0.8,
    max_tokens: int = 300,
) -> str:
    """High‑level entry point used by the Telegram layer."""
    
    logger.info("Получен запрос: %s", user_query)

    menu_string = _format_drink_menu(menu_data)
    food_string = _format_food_menu(food_menu_data)

    updates_string = f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}" if daily_updates else "нет оперативных данных"
    context_string = f"Время суток — {context_info.get('time_of_day', 'неизвестно')}, Повод визита — {context_info.get('occasion', 'неизвестен')}" if context_info else "контекст неизвестен"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _create_system_prompt(updates_string, context_string)}
    ]

    if conversation_history:
        messages.extend(conversation_history)

    user_content = f"Вот меню для справки:\nНастойки:\n{menu_string}\n\nЕда:\n{food_string}\n\nМой запрос: {user_query}" if menu_string or food_string else user_query
    messages.append({"role": "user", "content": user_content})

    try:
        logger.info("Отправка запроса в OpenAI API…")
        completion = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response_text = completion.choices[0].message.content
        logger.info("Ответ получен успешно.")
        return response_text

    except Exception as exc:
        logger.error("Ошибка при обращении к OpenAI API: %s", exc)
        return "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. Попробуй обратиться ко мне чуть позже."
