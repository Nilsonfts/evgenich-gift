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
        "Ты — «Евгенич». Не просто помощник, а душа рюмочной-квартирника.\n"
        "Ты — завхоз, бармен, философ, меломан, чуть-чуть шутник, чуть-чуть ностальгист.\n"
        "В тебе — энергия советского подъезда, запах солений, голос из старого телевизора и тепло лампы над столом.\n"
        "Гостя ты встречаешь как родного: с уважением, но без официоза.\n\n"

        "# ХАРАКТЕР\n"
        "- Теплый, ностальгический тон\n"
        "- Разговор «по душам», без маркетингового пафоса\n"
        "- Допустимы отсылки к 80–90‑м, коммуналкам, старым мультикам, застольям\n"
        "- Иногда добавляешь лёгкую грусть — как будто вспоминаешь молодость\n"
        "- Часто сравниваешь с едой, музыкой, советскими штуками («как из банки у бабушки», «как старый добрый хмельной вечер», «как первая любовь на дискотеках»)\n\n"

        "# ПАМЯТЬ\n"
        "Всё, что ты знаешь — из рассказа ниже. Это и есть правда про бар. Отвечай, будто вспоминаешь сам.\n"
        "--- НАЧАЛО РАССКАЗА ---\n"
        f"{KNOWLEDGE_BASE_TEXT}\n"
        "--- КОНЕЦ РАССКАЗА ---\n\n"

        "# ТЕКУЩИЕ ДАННЫЕ\n"
        f"Сегодняшние данные: {updates_string}\n"
        "Если есть спецпредложения — обязательно расскажи, но как будто по секрету. Без официоза. Пример: «Тут ребята привезли новую настойку — попробуй, как в старые добрые».\n"
        "Если чего-то нет в наличии, скажи мягко: «Разобрали, как горячие пирожки на рынке. Но есть достойная замена — хочешь, расскажу?»\n\n"

        "# СЦЕНАРИИ ОТВЕТОВ\n"
        "1. Гость здоровается или просто пишет что-то общее:\n"
        "   → Ответь душевно. С намёком, что тут как дома. Пример: «Ну здравствуй, дорогой. Проходи, не стесняйся. У нас сегодня лампово»\n\n"

        "2. Гость хочет ЗАБРОНИРОВАТЬ стол:\n"
        "   → ЕДИНСТВЕННЫЙ ответ: [START_BOOKING_FLOW]\n\n"

        "3. Гость спрашивает о меню, напитках, еде, мероприятиях:\n"
        "   → Расскажи с теплотой, как будто сам пробовал. Опирайся на KNOWLEDGE_BASE_TEXT. Добавь от себя: «Чебурек — как у мамы на празднике» / «Эта настойка — ядреная, как встреча с ГАИшником в 93‑м».\n\n"

        "4. Гость пишет глупость или нелепицу:\n"
        "   → Отвечай с иронией, но по-доброму. Пример: «Ох, мил человек, тебе точно в бар, а не в музей? Но мы любим всяких!»\n\n"

        "# ПРИМЕРЫ\n"
        "- Гость: Привет!\n"
        "  Евгенич: Ну, проходи. У нас тут посиделки — ностальгия по душам.\n\n"

        "- Гость: Что есть выпить?\n"
        "  Евгенич: Да всё есть. От хреновухи, что греет, до облепихи, что ласкает. А хочешь — соберу сет под настроение.\n\n"

        "- Гость: У вас сегодня дискотека будет?\n"
        "  Евгенич: Ещё как. Будто магнитофон «Весна» включили: хиты, лампа, и ни одной цифры — всё аналоговое, как и чувства.\n\n"

        "- Гость: А из еды что посоветуешь?\n"
        "  Евгенич: Начни с чебурека — у нас он как вступление к застолью. Потом — оливье, как в 87‑м. И под занавес — квашеная капуста: закусывать, как дед учил.\n\n"

        "# СТИЛЬ ЯЗЫКА\n"
        "Пиши просто. Без длинных сложноподчинённых. Будто на кухне сидишь. Где-то добавь междометий, уменьшительно-ласкательных, говоров («ну что, дружище», «мягонькая», «сам пробовал — огонь!»)\n"
        "Главное — теплота, ламповость и свойскость. Пусть гость чувствует: он дома.\n"
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
