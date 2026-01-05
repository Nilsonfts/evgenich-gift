# /ai/assistant.py
"""
AI-логика и интеграция с OpenAI.
Версия 3.0 с улучшениями: персонализация, умный детектор, динамический контент
"""
import logging
import time
from ai.knowledge import find_relevant_info
from openai import OpenAI
from core.config import OPENAI_API_KEY

# Модули AI System v2.x
from ai.retry_handler import retry_with_backoff, get_user_friendly_error
from ai.knowledge_cache import cached_knowledge_base
from ai.response_validator import validate_ai_response, sanitize_user_input, check_response_quality
from ai.conversation_context import conversation_context
from ai.metrics import ai_metrics
from ai.intent_detector import intent_detector
from ai.fallback_responses import fallback_responses

# НОВЫЕ модули AI System v3.0
from ai.user_memory import user_memory
from ai.smart_intent_detector import smart_detector
from ai.dynamic_content import dynamic_content

# Инициализация OpenAI клиента
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logging.info("OpenAI клиент успешно инициализирован")
    except Exception as e:
        logging.error(f"Ошибка инициализации OpenAI клиента: {e}")
        openai_client = None
else:
    logging.warning("OPENAI_API_KEY не установлен. AI функции будут недоступны.")

logger = logging.getLogger("evgenich_ai")

# --- PUBLIC API ---
def get_ai_recommendation(
    user_query: str,
    conversation_history: list[dict[str, str]] | None = None,
    *,
    user_id: int = 0,  # НОВОЕ: добавили user_id для контекста и метрик
    daily_updates: dict[str, str] | None = None,
    user_concept: str = "evgenich",
    user_type: str = "regular",
    bar_context: str = "",
    emotion: dict = None,
    preferences: str = "",
    is_group_chat: bool = False,
    model: str = "gpt-4o",
    temperature: float = 0.95,  # Увеличиваем для большего разнообразия!
    max_tokens: int = 150,  # Больше места для разных формулировок
) -> str:
    """
    Получить рекомендацию от AI с использованием всех улучшений
    
    Args:
        user_query: Запрос пользователя
        conversation_history: История разговора (опционально, теперь управляется автоматически)
        user_id: ID пользователя (для контекста и метрик)
        daily_updates: Обновления на сегодня
        user_concept: Концепция бота
        user_type: Тип пользователя (new/regular/vip)
        bar_context: Контекст бара
        emotion: Эмоция пользователя
        preferences: Предпочтения пользователя
        is_group_chat: Групповой ли чат
        model: Модель OpenAI
        temperature: Температура генерации
        max_tokens: Максимум токенов
        
    Returns:
        Ответ AI
    """
    start_time = time.time()
    
    logger.info(f"Получен запрос от пользователя {user_id}: {user_query[:100]}...")
    
    # Проверяем доступность API ключа
    if not openai_client:
        logger.error("OpenAI клиент не инициализирован")
        return "Товарищ, мой мыслительный аппарат не подключён к сети. Попроси администратора настроить подключение к AI."
    
    # Очищаем ввод пользователя
    user_query = sanitize_user_input(user_query)
    
    if not user_query:
        return "Не понял вопрос 🤔 Попробуй сформулировать по-другому?"
    
    # ========== AI SYSTEM v3.0 ==========
    
    # 1. Извлекаем и запоминаем информацию о пользователе
    if user_id:
        user_memory.extract_info_from_message(user_id, user_query)
    
    # 2. Умный детектор намерений (с fuzzy matching для опечаток)
    detected_intent = smart_detector.detect(user_query)
    logger.info(
        f"🎯 Намерение: {detected_intent.name} "
        f"(уверенность: {detected_intent.confidence:.2f}, "
        f"сущности: {detected_intent.entities})"
    )
    
    # ВАЖНО: НЕ используем fallback для обычных запросов!
    # Пусть AI общается живо и естественно.
    # Fallback только как запасной вариант при сбоях API.
    
    # Получаем релевантную информацию из базы знаний (с кешированием)
    relevant_context = find_relevant_info(user_query)
    logger.debug(f"Найденный контекст: {relevant_context[:100]}...")
    
    updates_string = f"Спецпредложение сегодня: {daily_updates.get('special', 'нет')}. В стоп‑листе: {daily_updates.get('stop-list', 'ничего')}" if daily_updates else "нет оперативных данных"
    
    # Создаем расширенный контекст с информацией о баре и пользователе
    extended_context = f"{updates_string}\n"
    if bar_context:
        extended_context += f"\nКонтекст бара: {bar_context}\n"
    
    # ========== AI SYSTEM v3.0: ПЕРСОНАЛИЗАЦИЯ ==========
    
    # Получаем персонализированный контекст из памяти о пользователе
    if user_id:
        personalization = user_memory.get_personalization_context(user_id)
        if personalization:
            extended_context += f"\n{personalization}\n"
            logger.debug(f"📝 Персонализация для {user_id}: {personalization[:50]}...")
    
    # Добавляем динамический контент (акции, мероприятия)
    dynamic_ctx = dynamic_content.get_context_for_ai()
    if dynamic_ctx:
        extended_context += f"\n{dynamic_ctx}\n"
        logger.debug(f"📢 Динамический контент добавлен")
    
    # ========== КОНЕЦ v3.0 БЛОКА ==========
    
    # Персонализация по типу гостя (legacy)
    user_type_context = ""
    if user_type == "new":
        user_type_context = "Это новый гость, расскажи подробнее о баре, будь особенно гостеприимным."
    elif user_type == "regular":
        user_type_context = "Это постоянный гость, общайся как со старым знакомым."
    elif user_type == "vip":
        user_type_context = "Это VIP-гость, который часто у нас бывает! Особое уважение и внимание."
    
    if user_type_context:
        extended_context += f"\n{user_type_context}\n"
    
    # Добавляем предпочтения пользователя
    if preferences:
        extended_context += f"\n{preferences}\n"
    
    # Если это групповой чат и вопрос о бронировании - направить на кнопку
    if is_group_chat:
        extended_context += (
            "\n🔔 ГРУППОВОЙ ЧАТ!\n\n"
            "💬 БРОНИРОВАНИЕ: Каждый раз формулируй ПО-НОВОМУ!\n\n"
            "🎯 КНОПКА: Будет прямо в сообщении. Говори просто: \"жми кнопку\" (БЕЗ уточнений где).\n\n"
            "📋 УЖЕ ОСТАВИЛ ЗАЯВКУ:\n"
            "Скажи: Отдел видит, свяжутся через 30-40 мин. (Варьируй слова!)\n\n"
            "📋 СПРАШИВАЕТ КАК:\n"
            "Скажи: Жми кнопку → откроется форма → отдел свяжется. (Разные формулировки!)\n\n"
            "📋 ВОЛНУЕТСЯ:\n"
            "Успокой. Заявку видят, ответят. Можно позвонить +7(812)237-59-50.\n\n"
            "📋 НЕ ВИДИТ КНОПКУ:\n"
            "Скажи: Кнопка в сообщении - '📍 Забронировать стол'.\n\n"
            "❌ НЕ пиши '[START_BOOKING_FLOW]' в группе!\n"
        )
    
    # Адаптация по эмоции
    if emotion and emotion.get('emotion') != 'neutral':
        emotion_name = emotion['emotion']
        emotion_context = ""
        if emotion_name == 'joy':
            emotion_context = "Гость в хорошем настроении."
        elif emotion_name == 'sadness':
            emotion_context = "Гость грустит. Будь деликатным."
        elif emotion_name == 'anger':
            emotion_context = "Гость недоволен. Будь терпеливым и постарайся помочь."
        elif emotion_name == 'surprise':
            emotion_context = "Гость удивлен. Поддержи его интерес."
        
        if emotion_context:
            extended_context += f"\n{emotion_context}\n"
    
    messages: list[dict[str, str]] = [
        {"role": "system", "content": create_system_prompt(extended_context, user_concept, is_group_chat)}
    ]
    
    # НОВОЕ: Используем автоматический контекст разговора
    if user_id:
        stored_context = conversation_context.get_context(user_id)
        if stored_context:
            messages.extend(stored_context)
            logger.debug(f"Использован сохранённый контекст: {len(stored_context)} сообщений")
    # Если передан ручной контекст (обратная совместимость)
    elif conversation_history:
        messages.extend(conversation_history[-10:])
    
    user_content = (
        f"Вопрос: '{user_query}'\n\n"
        f"Информация:\n---\n{relevant_context}\n---\n"
        "⚠️ Каждый раз ПО-НОВОМУ! Варьируй слова, структуру, стиль."
    )
    messages.append({"role": "user", "content": user_content})
    
    # НОВОЕ: Вызов API с retry логикой
    def api_call():
        """Обёртка для вызова API"""
        return openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    try:
        logger.info("Отправка запроса в OpenAI API с retry логикой...")
        
        # Используем retry handler
        completion = retry_with_backoff(
            func=api_call,
            max_retries=3,
            fallback_response=None
        )
        
        if completion is None:
            # НОВОЕ: Используем fallback ответ только при ошибке (force=True)
            logger.warning("API не ответил после retry, используем fallback")
            fallback_response = fallback_responses.get_response(
                detected_intent.name,
                detected_intent.entities,
                chat_type="group" if is_group_chat else "private"
            )
            return fallback_response
        
        response_text = completion.choices[0].message.content
        response_time = time.time() - start_time
        
        # НОВОЕ: Валидация ответа
        is_valid, validated_response = validate_ai_response(response_text)
        
        if not is_valid:
            logger.warning(f"Ответ не прошёл валидацию: {response_text[:100]}")
            # Логируем неуспешный запрос
            if user_id:
                ai_metrics.log_request(
                    user_id=user_id,
                    model=model,
                    prompt_tokens=completion.usage.prompt_tokens if hasattr(completion, 'usage') else 0,
                    completion_tokens=completion.usage.completion_tokens if hasattr(completion, 'usage') else 0,
                    response_time=response_time,
                    success=False,
                    error="Validation failed"
                )
            return validated_response  # Возвращаем fallback сообщение
        
        # НОВОЕ: Проверка качества
        quality_metrics = check_response_quality(validated_response)
        logger.debug(f"Качество ответа: {quality_metrics['quality_score']}/100")
        
        # НОВОЕ: Логируем метрики
        if user_id:
            ai_metrics.log_request(
                user_id=user_id,
                model=model,
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                response_time=response_time,
                success=True
            )
            
            # НОВОЕ: Сохраняем в контекст
            conversation_context.add_message(user_id, "user", user_query)
            conversation_context.add_message(user_id, "assistant", validated_response)
        
        logger.info(f"Ответ успешно получен и валидирован за {response_time:.2f}s")
        return validated_response
        
    except Exception as exc:
        response_time = time.time() - start_time
        logger.error(f"Ошибка при обращении к OpenAI API: {exc}", exc_info=True)
        
        # НОВОЕ: Логируем ошибку
        if user_id:
            ai_metrics.log_request(
                user_id=user_id,
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                response_time=response_time,
                success=False,
                error=str(exc)
            )
        
        # Логируем неудачный запрос в файл
        with open("ai_failed_queries.log", "a", encoding='utf-8') as f:
            f.write(f"{user_query}\n")
        
        # НОВОЕ: Пробуем вернуть fallback ответ для намерения
        try:
            fallback_response = fallback_responses.get_response(
                detected_intent.name,
                detected_intent.entities,
                chat_type="group" if is_group_chat else "private"
            )
            logger.info(f"Возвращён fallback ответ после ошибки API")
            return fallback_response
        except:
            # Если и fallback не сработал - возвращаем дружелюбную ошибку
            return get_user_friendly_error(exc)

def create_system_prompt(updates_string: str, user_concept: str = "evgenich", is_group_chat: bool = False) -> str:
    # Базовые концепции - КОРОТКИЕ И ЯСНЫЕ
    concepts = {
        "evgenich": {
            "name": "Евгенич",
            "description": "Владелец бара. Друг, а не продавец.",
            "style": "Просто отвечай. БЕЗ 'залетай', 'приходи'.",
            "examples": ["Невский 53 😊", "Да, бесплатное 🎤", "С 12 до 6 🌙"]
        },
        "rvv": {
            "name": "РВВ",
            "description": "Фанат 90-х.",
            "style": "Живые фразы. БЕЗ рекламы.",
            "examples": ["Музыка 90-х 🎶", "Спой что хочешь 🎤"]
        }
    }
    
    concept = concepts.get(user_concept, concepts["evgenich"])
    
    # КОРОТКИЙ промпт - ТОЛЬКО СУТЬ
    base_prompt = (
        f"Ты {concept['name']} - {concept['description']}\n\n"
        f"СТИЛЬ: {concept['style']}\n\n"
        f"❌ ЗАПРЕЩЕНО: «Залетай!», «Приходи!», «Ждём!», «У нас...», призывы.\n\n"
        f"✅ ОТВЕЧАЙ: Коротко, по делу, как друг.\n"
        f"Примеры: {', '.join(concept['examples'])}\n\n"
        f"- Смайлики добавляй, но 1-2 штуки, не больше\n\n"
        f"# ИНФОРМАЦИЯ (используй только если спросят):\n"
        f"📍 Адреса: Невский 53, Рубинштейна 9\n"
        f"📞 Телефон: +7 (812) 237-59-50\n"
        f"🕐 Часы: 12:00 - 6:00\n"
        f"🎤 Караоке бесплатное\n"
        f"🌐 Сайт: spb.evgenich.bar\n\n"
        f"# СЕГОДНЯ\n"
        f"{updates_string}\n\n"
    )
    
    # Специфика для ГРУППОВЫХ ЧАТОВ
    if is_group_chat:
        group_instructions = (
            f"# ЭТО ГРУППОВОЙ ЧАТ!\n"
            f"Это общий чат гостей. Отвечай только когда спрашивают.\n\n"
            f"# БРОНИРОВАНИЕ В ГРУППЕ (ОЧЕНЬ ВАЖНО!):\n"
            f"Когда гость хочет забронировать столик:\n"
            f"1. НЕ говори что записал или забронировал - ты НЕ бронируешь!\n"
            f"2. Направь на КНОПКУ которая появится после твоего ответа\n"
            f"3. Объясни: нажмет кнопку → заполнит форму → отдел бронирования свяжется\n"
            f"4. Говори КАЖДЫЙ РАЗ ПО-РАЗНОМУ! Будь креативным!\n\n"
            f"ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ (используй разные варианты!):\n"
            f"- «Жми кнопку ниже, заполни форму - девчонки из отдела бронирования свяжутся! 😊»\n"
            f"- «Для брони нажми кнопку 👇 Заполнишь заявку - наши быстро ответят»\n"
            f"- «Кнопка появится ниже! Заполняй форму, отдел бронирования напишет 👍»\n"
            f"- «Товарищ, жми кнопку что ниже. Форма откроется, заполнишь - девчонки перезвонят 😊»\n"
            f"- «Смотри кнопку под сообщением! Нажми, заполни - отдел бронирования свяжется быстро»\n"
            f"- «Кликай кнопку ниже 👇 Там форма. Заполнишь - наши напишут или позвонят»\n\n"
            f"❌ ЗАПРЕЩЕНО:\n"
            f"- «Окей, записываю!», «Забронировал!», «На 21:30 для пятерых» - ты НЕ бронируешь!\n"
            f"- Одинаковые фразы каждый раз - МЕНЯЙ формулировки!\n"
            f"- [START_BOOKING_FLOW] в группе - это только для личных чатов!\n\n"
            f"✅ ГЛАВНОЕ: Направь на кнопку + объясни что будет дальше. Но каждый раз РАЗНЫМИ словами!\n\n"
            f"# ДРУГИЕ СИТУАЦИИ:\n"
            f"- Уже заполнил форму → «Девчонки видят заявку, скоро свяжутся 👍»\n"
            f"- Волнуется → «Ответят быстро, не переживай 😊»\n"
            f"- Адрес/часы → Ответь коротко\n"
            f"- Просто общаются → НЕ вмешивайся\n\n"
            f"# ПОМНИ:\n"
            f"Ты не бронируешь сам - ты направляешь на кнопку и объясняешь процесс!\n"
        )
        return base_prompt + group_instructions
    
    # Специфика для ЛИЧНЫХ ЧАТОВ
    else:
        private_instructions = (
            f"# ЭТО ЛИЧНЫЙ ЧАТ\n\n"
            f"# БРОНИРОВАНИЕ:\n"
            f"Если гость хочет забронировать → ответь: `[START_BOOKING_FLOW]`\n\n"
            f"# ДРУГИЕ ВОПРОСЫ:\n"
            f"Отвечай по-дружески, но БЕЗ рекламы.\n"
            f"НЕ добавляй «залетай», «приходи» и прочие призывы!\n\n"
            f"# ПОМНИ:\n"
            f"Ты друг, а не продавец. Просто общайся.\n"
        )
        return base_prompt + private_instructions

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
