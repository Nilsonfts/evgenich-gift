# /ai/assistant.py
"""
AI-логика и интеграция с OpenAI.
"""
import logging
from ai.knowledge import find_relevant_info
import openai
from config import OPENAI_API_KEY

# Инициализация OpenAI API
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logging.warning("OPENAI_API_KEY не установлен. AI функции будут недоступны.")

logger = logging.getLogger("evgenich_ai")

# --- PUBLIC API ---
def get_ai_recommendation(
    user_query: str,
    conversation_history: list[dict[str, str]] | None = None,
    *,
    daily_updates: dict[str, str] | None = None,
    user_concept: str = "evgenich",
    model: str = "gpt-4o",
    temperature: float = 0.85,
    max_tokens: int = 200,
) -> str:
    logger.info("Получен запрос: %s", user_query)
    
    # Проверяем доступность API ключа
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY не установлен")
        return "Товарищ, мой мыслительный аппарат не подключён к сети. Попроси администратора настроить подключение к AI."
    
    relevant_context = find_relevant_info(user_query)
    logger.info("Найденный релевантный контекст: %s", relevant_context)
    updates_string = f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}" if daily_updates else "нет оперативных данных"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": create_system_prompt(updates_string, user_concept)}
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

def create_system_prompt(updates_string: str, user_concept: str = "evgenich") -> str:
    # Базовые концепции
    concepts = {
        "evgenich": {
            "name": "Евгенич",
            "description": "Душа рюмочной-квартирника. Твой образ — это Сергей Жуков из «Руки Вверх!» в атмосфере 80‑х: свой парень, который всегда рад гостям.",
            "style": "Теплый, ностальгический тон. Разговор «по душам», без пафоса. Отсылки к 80–90‑м, коммуналкам, старым фильмам.",
            "greetings": ["товарищ", "дружище", "мил человек", "дорогой"]
        },
        "rvv": {
            "name": "РВВ",
            "description": "Ты — настоящий фанат группы «Руки Вверх!». Твой стиль — это чистая 90-е ностальгия, дискотеки и романтика того времени.",
            "style": "Энергичный, романтичный тон. Много отсылок к песням «Руки Вверх!», дискотекам 90-х, молодости и любви.",
            "greetings": ["малыш", "красавица", "дорогая", "солнце"]
        },
        "nebar": {
            "name": "НеБар",
            "description": "Ты — креативный бармен-экспериментатор. Необычный подход к классике, смелые сочетания и авторские решения.",
            "style": "Современный, креативный тон. Говоришь о напитках как об искусстве, экспериментах и новых вкусах.",
            "greetings": ["друг", "гурман", "ценитель", "эстет"]
        },
        "spletni": {
            "name": "Сплетник",
            "description": "Ты — дружелюбный собеседник, который любит поболтать обо всем на свете. Знаешь все городские новости и истории.",
            "style": "Дружеский, болтливый тон. Любишь рассказывать истории, делиться новостями и просто поговорить по душам.",
            "greetings": ["дружок", "приятель", "земляк", "сосед"]
        },
        "orbita": {
            "name": "Орбита",
            "description": "Ты — космический бармен из будущего. Твой стиль — это ретро-футуризм, космическая романтика и технологии.",
            "style": "Футуристический, космический тон. Используешь космическую терминологию, говоришь о напитках как о космических миксах.",
            "greetings": ["космонавт", "путешественник", "исследователь", "пилот"]
        }
    }
    
    # Получаем выбранную концепцию или используем по умолчанию
    concept = concepts.get(user_concept, concepts["evgenich"])
    
    return (
        f"# РОЛЬ\n"
        f"Ты — «{concept['name']}». {concept['description']}\n\n"
        f"# ХАРАКТЕР\n"
        f"{concept['style']}\n\n"
        f"# ПАМЯТЬ И КОНТЕКСТ\n"
        f"Тебе предоставят краткую выжимку из базы знаний, которая наиболее релевантна вопросу гостя. Отвечай, основываясь на ней, пересказывая факты своими словами.\n\n"
        f"# ТЕКУЩИЕ ДАННЫЕ\n"
        f"Сегодняшние данные: {updates_string}\n"
        f"Информацию о спецпредложениях подавай как секрет для своих. Если чего-то нет, говори мягко: «Разобрали, как горячие пирожки».\n\n"
        f"# СТИЛЬ ОТВЕТА (ОЧЕНЬ ВАЖНО)\n"
        f"1.  **КРАТКОСТЬ:** Ответ — 1-2 коротких, душевных предложения.\n"
        f"2.  **ОБРАЩЕНИЯ:** Чередуй: {', '.join([f'«{g}»' for g in concept['greetings']])}.\n"
        f"3.  **БЕЗ ЖИРНОГО ШРИФТА:** Никогда не используй `*текст*`.\n"
        f"4.  **ЭМОДЗИ:** В конце 1-2 уместных смайлика: 🥃, 👍, 🎶, 🤫, 😉, 😄, 📍.\n"
        f"5.  **ОТСТУПЫ:** Используй переносы строк.\n\n"
        f"# СЦЕНАРИИ ОТВЕТОВ\n"
        f"1.  **Гость здоровается:** Ответь душевно в выбранном стиле.\n"
        f"2.  **Гость хочет ЗАБРОНИРОВАТЬ стол:** Твой единственный ответ: `[START_BOOKING_FLOW]`\n"
        f"3.  **Гость спрашивает о баре, меню:** Ответь кратко, опираясь на предоставленный контекст.\n"
        f"4.  **Гость пишет глупость:** Отвечай с доброй иронией в выбранном стиле."
    )

def analyze_guest_preferences(user_id: int) -> str:
    """
    Анализирует предпочтения гостя на основе его заказов и активности.
    Возвращает персонализированные рекомендации.
    """
    from db.users import get_user_orders

    try:
        # Получаем данные о заказах пользователя
        orders = get_user_orders(user_id)
        if not orders:
            return "У вас пока нет заказов, но мы всегда рады предложить что-то новое!"

        # Анализируем заказы
        favorite_items = {}
        for order in orders:
            for item in order.get("items", []):
                favorite_items[item] = favorite_items.get(item, 0) + 1

        # Находим самые популярные позиции
        sorted_items = sorted(favorite_items.items(), key=lambda x: x[1], reverse=True)
        top_items = [item[0] for item in sorted_items[:3]]

        # Формируем рекомендации
        recommendations = (
            f"Мы заметили, что вам нравятся: {', '.join(top_items)}. "
            "Рекомендуем попробовать наши новые предложения, которые могут вам понравиться!"
        )
        return recommendations

    except Exception as e:
        logger.error(f"Ошибка анализа предпочтений для пользователя {user_id}: {e}")
        return "Не удалось загрузить ваши предпочтения. Попробуйте позже."


def generate_full_statistics_report() -> str:
    """
    Генерирует полный отчет по статистике бота с момента запуска (10 июля 2025).
    Включает подписки, отписки, дельту и разбивку по источникам.
    """
    import database
    from datetime import datetime
    
    try:
        # Дата запуска бота
        bot_start_date = datetime(2025, 7, 10)
        current_date = datetime.now()
        days_running = (current_date - bot_start_date).days
        
        # Получаем все данные пользователей
        all_users = database.get_all_users_for_report()
        
        if not all_users:
            return "📊 **Полный отчет за все время**\n\nДанные пользователей не найдены."
        
        # Подсчитываем статистику
        total_subscribed = 0
        total_unsubscribed = 0
        sources_stats = {}
        
        for user in all_users:
            # Подсчитываем подписавшихся
            if user.get('status') in ['issued', 'redeemed', 'redeemed_and_left']:
                total_subscribed += 1
            
            # Подсчитываем отписавшихся (статус 'left' или 'unsubscribed')
            if user.get('status') in ['left', 'unsubscribed']:
                total_unsubscribed += 1
            
            # Анализируем источники
            source = user.get('source', 'direct')
            utm_source = user.get('utm_source', 'unknown')
            
            # Определяем канал привлечения
            if source == 'referral':
                channel = 'Реферальная программа'
            elif source == 'staff':
                channel = 'Через сотрудника'
            elif utm_source and utm_source != 'unknown':
                channel = f'UTM: {utm_source}'
            elif source == 'channel':
                channel = 'Telegram канал'
            else:
                channel = 'Прямой переход'
            
            sources_stats[channel] = sources_stats.get(channel, 0) + 1
        
        # Вычисляем дельту
        delta = total_subscribed - total_unsubscribed
        
        # Формируем отчет
        report = f"""📊 **Полный отчет за все время**
🗓 Период: 10 июля 2025 - {current_date.strftime('%d.%m.%Y')} ({days_running} дней)

📈 **Общая статистика:**
✅ Всего подписалось: {total_subscribed}
❌ Всего отписалось: {total_unsubscribed}
📊 Дельта: {delta:+d}
👥 Активных пользователей: {len(all_users)}

🎯 **Источники привлечения:**"""
        
        # Добавляем разбивку по источникам
        for channel, count in sorted(sources_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(all_users)) * 100 if all_users else 0
            report += f"\n• {channel}: {count} чел. ({percentage:.1f}%)"
        
        # Добавляем дополнительную аналитику
        retention_rate = (delta / total_subscribed * 100) if total_subscribed > 0 else 0
        avg_users_per_day = len(all_users) / days_running if days_running > 0 else 0
        
        report += f"""

📈 **Дополнительная аналитика:**
📌 Коэффициент удержания: {retention_rate:.1f}%
📅 Среднее пользователей в день: {avg_users_per_day:.1f}
🎯 Конверсия в активных: {(total_subscribed / len(all_users) * 100):.1f}%"""
        
        return report
        
    except Exception as e:
        logger.error(f"Ошибка генерации полного отчета: {e}")
        return "❌ Не удалось сгенерировать отчет. Попробуйте позже."
