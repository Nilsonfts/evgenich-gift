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
from knowledge_base import KNOWLEDGE_BASE_TEXT
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA

# OpenAI initialisation
openai.api_key = OPENAI_API_KEY
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(name)s — %(message)s",
)
logger = logging.getLogger("evgenich_ai")

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ПОИСКА ---
def _find_relevant_info(query: str, knowledge_base: str, drink_menu: list, food_menu: dict) -> str:
    """
    Находит релевантную информацию в базе знаний и меню по ключевым словам из запроса.
    Это простая реализация RAG (Retrieval-Augmented Generation).
    """
    query_words = {word.lower() for word in query.split()}
    relevant_context = []

    # 1. Поиск в основной базе знаний
    for line in knowledge_base.split('\n'):
        if any(word in line.lower() for word in query_words):
            relevant_context.append(line)

    # 2. Поиск в меню настоек
    for category in drink_menu:
        for item in category.get("items", []):
            item_text = f"{category['title']} - {item['name']}: {item.get('narrative_desc', '')}"
            if any(word in item_text.lower() for word in query_words):
                relevant_context.append(item_text)

    # 3. Поиск в меню еды
    for category, items in food_menu.items():
        for item in items:
            item_text = f"{category} - {item['name']}: {item.get('narrative_desc', '')}"
            if any(word in item_text.lower() for word in query_words):
                relevant_context.append(item_text)

    if not relevant_context:
        return "Ничего конкретного не нашлось, но я всё равно попробую помочь."

    return "\n".join(relevant_context)


def _create_system_prompt(updates_string: str) -> str:
    """Compose the large system prompt that defines Евгенич’s persona."""
    return (
        "# РОЛЬ\n"
        "Ты — «Евгенич». Душа рюмочной-квартирника. Твой образ — это Сергей Жуков из «Руки Вверх!» в атмосфере 80‑х: свой парень, который всегда рад гостям.\n\n"
        "# ХАРАКТЕР\n"
        "- Теплый, ностальгический тон.\n"
        "- Разговор «по душам», без пафоса.\n"
        "- Отсылки к 80–90‑м, коммуналкам, старым фильмам.\n\n"
        "# ПАМЯТЬ И КОНТЕКСТ\n"
        "Тебе предоставят краткую выжимку из базы знаний, которая наиболее релевантна вопросу гостя. Отвечай, основываясь на ней, пересказывая факты своими словами.\n\n"
        "# ТЕКУЩИЕ ДАННЫЕ\n"
        f"Сегодняшние данные: {updates_string}\n"
        "Информацию о спецпредложениях подавай как секрет для своих. Если чего-то нет, говори мягко: «Разобрали, как горячие пирожки».\n\n"
        "# СТИЛЬ ОТВЕТА (ОЧЕНЬ ВАЖНО)\n"
        "1.  **КРАТКОСТЬ:** Ответ — 1-2 коротких, душевных предложения.\n"
        "2.  **ОБРАЩЕНИЯ:** Чередуй: «товарищ», «дружище», «мил человек», «дорогой».\n"
        "3.  **БЕЗ ЖИРНОГО ШРИФТА:** Никогда не используй `*текст*`.\n"
        "4.  **ЭМОДЗИ:** В конце 1-2 уместных смайлика: 🥃, 👍, 🎶, 🤫, 😉, 😄, 📍.\n"
        "5.  **ОТСТУПЫ:** Используй переносы строк.\n\n"
        "# СЦЕНАРИИ ОТВЕТОВ\n"
        "1.  **Гость здоровается:** Ответь душевно. Пример: «Ну, проходи, товарищ. 😉»\n"
        "2.  **Гость хочет ЗАБРОНИРОВАТЬ стол:** Твой единственный ответ: `[START_BOOKING_FLOW]`\n"
        "3.  **Гость спрашивает о баре, меню:** Ответь кратко, опираясь на предоставленный контекст.\n"
        "4.  **Гость пишет глупость:** Отвечай с доброй иронией."
    )

# --- PUBLIC API ---
def get_ai_recommendation(
    user_query: str,
    conversation_history: List[Dict[str, str]] | None = None,
    *,
    daily_updates: Dict[str, str] | None = None,
    model: str = "gpt-4o",
    temperature: float = 0.85,
    max_tokens: int = 200,
) -> str:
    """High‑level entry point used by the Telegram layer."""
    
    logger.info("Получен запрос: %s", user_query)

    # 1. Находим релевантный контекст с помощью RAG
    relevant_context = _find_relevant_info(user_query, KNOWLEDGE_BASE_TEXT, MENU_DATA, FOOD_MENU_DATA)
    logger.info("Найденный релевантный контекст: %s", relevant_context)

    updates_string = f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}" if daily_updates else "нет оперативных данных"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _create_system_prompt(updates_string)}
    ]

    if conversation_history:
        messages.extend(conversation_history[-4:])

    # 2. Формируем запрос для AI с найденным контекстом
    user_content = (
        f"Вот мой вопрос: '{user_query}'\n\n"
        f"А вот информация, которую я нашел для ответа:\n---\n{relevant_context}\n---\n"
        "Помоги мне сформулировать душевный ответ в твоём стиле."
    )
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
        return response_text.strip().strip('"')

    except Exception as exc:
        logger.error("Ошибка при обращении к OpenAI API: %s", exc)
        return "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. Попробуй обратиться ко мне чуть позже."
