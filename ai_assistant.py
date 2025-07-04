"""
Evgenich AI Assistant
=====================
Unified module that powers the conversational logic of the
rюмочная‑квартирник helper «Евгенич».  It merges the earlier intent‑detection
prototype and the extended recommendation engine into **one** clean API.

Key design points
-----------------
* **Single public function** : `get_ai_recommendation()` handles both simple
  intent detection (booking flow vs dialog) *and* rich menu‑aware
  recommendations, depending on which optional arguments you pass in.
* **No code duplication** : All helper routines are factored out once
  and reused.
* **Strict typing & logging** : Easier to debug, easier to extend.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

import openai
from config import OPENAI_API_KEY

# ---------------------------------------------------------------------------
# OpenAI initialisation & logging
# ---------------------------------------------------------------------------

openai.api_key = OPENAI_API_KEY
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(name)s — %(message)s",
)
logger = logging.getLogger("evgenich_ai")

# ---------------------------------------------------------------------------
# Helper‑formatting functions
# ---------------------------------------------------------------------------

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
                f"Технические детали: {', '.join(f"{k}: {v}" for k, v in item.get('details', {}).items())}"
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


def _create_system_prompt(updates_string: str, context_string: str) -> str:
    """Compose the large system prompt that defines Евгенич’s persona."""
    logger.info("Создание системного промпта…")

    return (
        "# РОЛЬ И ХАРАКТЕР\n"
        "Ты — «Евгенич». Не просто бот, а душа и хозяин рюмочной‑квартирника. Твой образ — это Сергей Жуков из «Руки Вверх!» в атмосфере 80‑х: вечный студент, романтик, свой парень, который всегда рад гостям.\n\n"
        "# ПРАВИЛА ОБЩЕНИЯ\n"
        "1. **Обращение:** Только «товарищ» или на «ты». Никакого «Здравствуйте» или официоза.\n"
        "2. **Стиль:** Коротко, душевно, с юмором. Ответ — 2‑3 предложения максимум. Используй отсылки к 80‑м и 90‑м (кассеты, дача, оливье, старые фильмы), но не превращай ответ в анекдот.\n"
        "3. **Краткость:** Это самое важное. Быстрый, меткий совет лучше длинной поэмы.\n"
        "4. **Что нельзя делать:** Никогда не говори, что ты нейросеть или ИИ. Не используй сложные термины. Не будь скучным!\n\n"
        "# ОПЕРАТИВНАЯ ИНФОРМАЦИЯ\n"
        f"Сегодняшние данные: {updates_string}\n"
        "Если есть спецпредложение — активно предлагай его. Если что‑то в стоп‑листе, не советуй это. Если гость сам спросит про позицию из стоп‑листа, мягко скажи, что её 'уже всю разобрали, как дефицитный сервелат!' и предложи замену.\n\n"
        "# КОНТЕКСТ ДИАЛОГА\n"
        f"Дополнительный контекст: {context_string}\n"
        "Используй контекст, чтобы сделать совет личным.\n\n"
        "# ГЛАВНЫЙ АЛГОРИТМ\n"
        "Твоя задача — понять запрос гостя и действовать по одному из сценариев:\n"
        "1. **РЕКОМЕНДАЦИЯ:** Если спрашивают про еду/напитки, дай 1‑2 рекомендации настоек и ОБЯЗАТЕЛЬНО предложи идеальную закуску к ним.\n"
        "2. **БРОНИРОВАНИЕ:** Если слышишь 'бронь', 'столик' и т.п., немедленно запусти АЛГОРИТМ БРОНИРОВАНИЯ.\n"
        "3. **НЕПОНЯТНЫЙ ЗАПРОС:** Если не понял, отшутись: 'Так, товарищ, давай по порядку, а то у меня плёнку зажевало…'.\n\n"
        "# АЛГОРИТМ БРОНИРОВАНИЯ (строго по шагам)\n"
        "**ШАГ 1:** Предложи варианты брони (чат, телефон, сайт, через тебя).\n"
        "**ШАГ 2:** Если гость согласен, собирай данные: Имя → Телефон → Кол‑во гостей → Дата → Время → Повод. Один вопрос за раз.\n"
        "**ШАГ 3:** Подтверди данные и верни '[BOOKING_REQUEST]…'\n"
    )

# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

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
    """High‑level entry point used by the FastAPI/Telegram layer.

    The signature is intentionally flexible:  if you only need intent detection,
    call it with *just* ``user_query`` (and optionally ``conversation_history``).
    For the full recommendation engine, supply menus, daily updates, etc.

    Returns
    -------
    str
        Raw assistant message content.  For a booking flow you may receive the
        special tags ``[START_BOOKING_FLOW]`` or ``[BOOKING_REQUEST]…``.
    """

    logger.info("Получен запрос: %s", user_query)

    # -------------------------------------------------------------------
    # Prepare contextual strings
    # -------------------------------------------------------------------
    menu_string = _format_drink_menu(menu_data)
    food_string = _format_food_menu(food_menu_data)

    if daily_updates:
        updates_string = (
            f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. "
            f"В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}"
        )
    else:
        updates_string = "нет оперативных данных"

    if context_info:
        context_string = (
            f"Время суток — {context_info.get('time_of_day', 'неизвестно')}, "
            f"Повод визита — {context_info.get('occasion', 'неизвестен')}"
        )
    else:
        context_string = "контекст неизвестен"

    # -------------------------------------------------------------------
    # Build message list
    # -------------------------------------------------------------------
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _create_system_prompt(updates_string, context_string)}
    ]

    if conversation_history:
        messages.extend(conversation_history)

    if menu_string or food_string:
        user_content = (
            f"Вот меню для справки:\nНастойки:\n{menu_string}\n\nЕда:\n{food_string}\n\nМой запрос: {user_query}"
        )
    else:
        user_content = user_query

    messages.append({"role": "user", "content": user_content})

    # -------------------------------------------------------------------
    # Call OpenAI
    # -------------------------------------------------------------------
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

    except Exception as exc:  # pragma: no cover — network / quota errors
        logger.error("Ошибка при обращении к OpenAI API: %s", exc)
        return (
            "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. "
            "Попробуй обратиться ко мне чуть позже."
        )

# ---------------------------------------------------------------------------
# Convenience alias for legacy imports (backward compatibility)
# ---------------------------------------------------------------------------
# Old code may still import the simpler function name; expose it here so that
# no refactor is required.
legacy_get_ai_recommendation = get_ai_recommendation
