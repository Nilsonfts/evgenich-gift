# /ai/assistant.py
"""
AI-логика и интеграция с OpenAI.
"""
import logging
from ai.knowledge import find_relevant_info
import openai

logger = logging.getLogger("evgenich_ai")

# --- PUBLIC API ---
def get_ai_recommendation(
    user_query: str,
    conversation_history: list[dict[str, str]] | None = None,
    *,
    daily_updates: dict[str, str] | None = None,
    model: str = "gpt-4o",
    temperature: float = 0.85,
    max_tokens: int = 200,
) -> str:
    logger.info("Получен запрос: %s", user_query)
    relevant_context = find_relevant_info(user_query)
    logger.info("Найденный релевантный контекст: %s", relevant_context)
    updates_string = f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}" if daily_updates else "нет оперативных данных"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": create_system_prompt(updates_string)}
    ]
    if conversation_history:
        messages.extend(conversation_history[-10:])  # расширенная история
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
        with open("ai_failed_queries.log", "a") as f:
            f.write(f"{user_query}\n")
        return "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. Попробуй обратиться ко мне чуть позже."

def create_system_prompt(updates_string: str) -> str:
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
