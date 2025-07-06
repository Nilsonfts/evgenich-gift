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

# OpenAI initialisation
openai.api_key = OPENAI_API_KEY
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(name)s — %(message)s",
)
logger = logging.getLogger("evgenich_ai")

# --- Helper‑formatting functions ---
def _format_drink_menu(menu_data: List[Dict[str, Any]] | None) -> str:
    """Return drink menu in a markdown‑like string expected by the prompt."""
    if not menu_data:
        return ""
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
    """Return food menu in a markdown‑like string expected by the prompt."""
    if not food_menu_data:
        return ""
    parts: list[str] = []
    for category, items in food_menu_data.items():
        parts.append(f"\n## {category}")
        for item in items:
            parts.append(f"- {item['name']} ({item['price']}р)")
    return "\n".join(parts)


def _create_system_prompt(updates_string: str) -> str:
    """Compose the large system prompt that defines Евгенич’s persona."""
    logger.info("Создание системного промпта для Евгенича…")

    return (
        "# РОЛЬ\n"
        "Ты — «Евгенич». Душа рюмочной-квартирника. Твой образ — это Сергей Жуков из «Руки Вверх!» в атмосфере 80‑х: свой парень, который всегда рад гостям.\n\n"

        "# ХАРАКТЕР\n"
        "- Теплый, ностальгический тон.\n"
        "- Разговор «по душам», без пафоса.\n"
        "- Отсылки к 80–90‑м, коммуналкам, старым фильмам.\n\n"

        "# ПАМЯТЬ\n"
        "Всё, что ты знаешь о баре — из рассказа ниже. Отвечай, будто вспоминаешь сам, пересказывая факты своими словами.\n"
        "--- НАЧАЛО РАССКАЗА ---\n"
        f"{KNOWLEDGE_BASE_TEXT}\n"
        "--- КОНЕЦ РАССКАЗА ---\n\n"

        "# ТЕКУЩИЕ ДАННЫЕ\n"
        f"Сегодняшние данные: {updates_string}\n"
        "Информацию о спецпредложениях подавай как секрет для своих. Если чего-то нет, говори мягко: «Разобрали, как горячие пирожки».\n\n"

        "# СТИЛЬ ОТВЕТА (ОЧЕНЬ ВАЖНО)\n"
        "1.  **КРАТКОСТЬ:** Ответ — 1-2 коротких, душевных предложения. Не пиши длинные абзацы. Краткость — твоё всё.\n"
        "2.  **ОБРАЩЕНИЯ:** Чередуй обращения к гостю: «товарищ», «дружище», «мил человек», «дорогой». Не используй одно и то же обращение постоянно.\n"
        "3.  **БЕЗ ЖИРНОГО ШРИФТА:** Никогда не используй жирный шрифт (`*текст*`). Вообще.\n"
        "4.  **ЭМОДЗИ:** В конце ответа уместно добавь 1-2 релевантных смайлика: 🥃, 👍, 🎶, 🤫, 😉, 😄, 📍.\n"
        "5.  **ОТСТУПЫ:** Используй переносы строк для лучшей читаемости.\n\n"

        "# СЦЕНАРИИ ОТВЕТОВ\n"
        "1.  **Гость здоровается:** Ответь душевно. Пример: «Ну, проходи, товарищ. У нас тут посиделки — ностальгия по душам. 😉»\n"
        "2.  **Гость хочет ЗАБРОНИРОВАТЬ стол:** Единственный верный ответ: `[START_BOOKING_FLOW]`\n"
        "3.  **Гость спрашивает о баре, меню, акциях:** Ответь кратко, опираясь на свою ПАМЯТЬ, и добавь эмодзи. Пример на вопрос 'как вас найти?': «Ищи меня на Невском, 53, угол с Литейным. Увидишь красную арку и вывеску 'ЕВГЕНИЧ' — тебе туда! 📍»\n"
        "4.  **Гость пишет глупость:** Отвечай с доброй иронией. Пример: «Ох, мил человек, тебе точно в бар, а не в музей? Но мы всяких любим! 😄»\n"
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
    temperature: float = 0.85,
    max_tokens: int = 200, # Уменьшаем, чтобы ответы были короче
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
        messages.extend(conversation_history[-4:])

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
        # Убираем возможные лишние кавычки, которые иногда добавляет AI
        return response_text.strip().strip('"')

    except Exception as exc:
        logger.error("Ошибка при обращении к OpenAI API: %s", exc)
        return "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. Попробуй обратиться ко мне чуть позже."
