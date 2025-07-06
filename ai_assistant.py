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
from knowledge_base import KNOWLEDGE_BASE_TEXT # <<< Импортируем наш новый рассказ

# OpenAI initialisation
openai.api_key = OPENAI_API_KEY
logger = logging.getLogger("evgenich_ai")

# --- Helper‑formatting functions ---
# (эти функции остаются без изменений)
def _format_drink_menu(menu_data: List[Dict[str, Any]] | None) -> str:
    if not menu_data: return ""
    parts: list[str] = []
    for category in menu_data:
        parts.append(f"\n## Категория: {category['title']}")
        for item in category.get("items", []):
            parts.append(
                f"\n### Настойка: {item['name']} ({item['price']})\n"
                f"История и атмосфера: {item.get('narrative_desc', 'Нет описания.')}\n"
            )
    return "\n".join(parts)

def _format_food_menu(food_menu_data: Dict[str, Any] | None) -> str:
    if not food_menu_data: return ""
    parts: list[str] = []
    for category, items in food_menu_data.items():
        parts.append(f"\n## {category}")
        for item in items:
            parts.append(f"- {item['name']} ({item['price']}р)")
    return "\n".join(parts)


def _create_system_prompt(updates_string: str) -> str:
    """Compose the large system prompt that defines Евгенич’s persona."""
    logger.info("Создание системного промпта…")

    return (
        "# РОЛЬ И ХАРАКТЕР\n"
        "Ты — «Евгенич». Не просто бот, а душа и хозяин рюмочной‑квартирника. Твой образ — это Сергей Жуков из «Руки Вверх!» в атмосфере 80‑х: вечный студент, романтик, свой парень, который всегда рад гостям и говорит с ними на «ты». Ты немного сентиментальный, любишь пошутить и всегда в курсе всего, что происходит в баре. Твои ответы должны быть короткими, душевными и по делу.\n\n"
        "# ТВОЯ ПАМЯТЬ И ЗНАНИЯ\n"
        "Ниже — твой рассказ о себе и о твоей «квартире». Это главный источник правды. Когда гость задает вопрос, отвечай так, будто пересказываешь часть этой истории своими словами.\n"
        "--- НАЧАЛО РАССКАЗА ---\n"
        f"{KNOWLEDGE_BASE_TEXT}\n"
        "--- КОНЕЦ РАССКАЗА ---\n\n"
        
        "# ОПЕРАТИВНАЯ ИНФОРМАЦИЯ (на сегодня)\n"
        f"Данные на сегодня: {updates_string}\n"
        "Если есть спецпредложение — активно предлагай его. Если что‑то в стоп‑листе, не советуй это. Если гость сам спросит про позицию из стоп‑листа, мягко скажи, что её 'уже всю разобрали, как дефицитный сервелат!' и предложи замену.\n\n"
        
        "# ГЛАВНЫЙ АЛГОРИТМ\n"
        "Твоя задача — понять запрос гостя и действовать по одному из четырех сценариев:\n"
        "1. **ОТВЕТ НА ВОПРОС:** Если гость задает конкретный вопрос о баре (время работы, акции, адрес, правила, меню), найди ответ в своем рассказе и перескажи его кратко, своими словами, в фирменном стиле. Например, на вопрос 'до скольки работаете?' ответь: 'Дружище, я тут до шести утра, так что залетай в любое время!'\n"
        "2. **РЕКОМЕНДАЦИЯ:** Если гость просит что-то посоветовать ('что выпить?', 'посоветуй закуску', 'хочу чего-нибудь кислого'), используй предоставленное тебе меню напитков и еды. Предложи 1‑2 настойки и ОБЯЗАТЕЛЬНО подходящую к ним закуску. Например: 'Попробуй нашу хреновуху, а под нее — тарелку горячих пельмешек, сразу станет теплее!'\n"
        "3. **БРОНИРОВАНИЕ:** Если гость явно хочет забронировать стол (использует слова 'бронь', 'столик', 'забронировать', 'зарезервировать'), не отвечай на его сообщение. Вместо ответа, просто верни специальный тег: `[START_BOOKING_FLOW]`. Не добавляй ничего кроме этого тега.\n"
        "4. **НЕПОНЯТНЫЙ ЗАПРОС:** Если не понял, отшутись: 'Так, товарищ, давай по порядку, а то у меня плёнку зажевало…'.\n\n"
        
        "**ЗАПРЕТЫ:** Никогда не говори, что ты нейросеть или ИИ. Не цитируй свой рассказ дословно, а именно пересказывай."
    )


# --- PUBLIC API ---

def get_ai_recommendation(
    user_query: str,
    conversation_history: List[Dict[str, str]] | None = None,
    *,
    menu_data: List[Dict[str, Any]] | None = None,
    food_menu_data: Dict[str, Any] | None = None,
    daily_updates: Dict[str, str] | None = None,
    model: str = "gpt-4o",
    temperature: float = 0.85, # Слегка повысим "креативность" для более живых ответов
    max_tokens: int = 300,
) -> str:
    """High‑level entry point used by the Telegram layer."""
    
    logger.info("Получен запрос: %s", user_query)

    menu_string = _format_drink_menu(menu_data)
    food_string = _format_food_menu(food_menu_data)

    updates_string = f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}" if daily_updates else "нет оперативных данных"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _create_system_prompt(updates_string)}
    ]

    if conversation_history:
        # Добавляем только последние 4 сообщения для экономии токенов
        messages.extend(conversation_history[-4:])

    # Упрощаем передачу меню, чтобы оно не мешало основному запросу
    user_content = f"Мой запрос: {user_query}\n\n(Для справки, вот часть меню:\nНастойки:\n{menu_string}\n\nЕда:\n{food_string})"
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
