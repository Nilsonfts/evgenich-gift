# /handlers/ai_logic.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from tinydb import TinyDB, Query

from ai.assistant import get_ai_recommendation
from ai.intent_recognition import detect_intent, detect_emotion, analyze_user_type
from ai.bar_context import get_current_bar_context, get_bar_info_text, get_location_info, get_working_hours
from ai.user_preferences import extract_preferences_from_text, get_preferences_text
from ai.proactive_messenger import proactive_messenger
import core.database as database
import texts
import keyboards
from core.config import REPORT_CHAT_ID, NASTOYKA_NOTIFICATIONS_CHAT_ID, BOOKING_NOTIFICATIONS_CHAT_ID, ALL_ADMINS

db = TinyDB('booking_data.json')
User = Query()

def register_ai_handlers(bot):
    """
    Регистрирует обработчики для AI-ассистента и других текстовых кнопок.
    """

    @bot.message_handler(func=lambda message: message.text == "🗣 Спроси у Евгенича")
    def handle_ai_prompt_button(message: types.Message):
        # Эта кнопка просто показывает подсказку как пользоваться AI
        # Реальная логика работы в группах обрабатывается в основном текстовом хендлере
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, texts.BOOKING_IN_PROGRESS_TEXT)
            return
        bot.reply_to(message, texts.AI_PROMPT_HINT)

    @bot.message_handler(content_types=['text'])
    def handle_text_query(message: types.Message):
        """
        Обрабатывает любой текстовый запрос, который не был перехвачен
        другими обработчиками (командами, шагами бронирования).
        """
        # --- ОТКЛЮЧЕНИЕ AI для служебных чатов ---
        try:
            # Проверяем все служебные чаты (отчеты, настойки, бронирования)
            service_chats = []
            if REPORT_CHAT_ID:
                service_chats.append(int(REPORT_CHAT_ID))
            if NASTOYKA_NOTIFICATIONS_CHAT_ID:
                service_chats.append(NASTOYKA_NOTIFICATIONS_CHAT_ID)
            if BOOKING_NOTIFICATIONS_CHAT_ID:
                service_chats.append(BOOKING_NOTIFICATIONS_CHAT_ID)
            
            # Явно отключаем AI для чата настоек
            service_chats.append(-1002813620544)  # Чат настоек - AI отключен
            
            if message.chat.id in service_chats:
                logging.info(f"AI отключен для служебного чата {message.chat.id}")
                return  # Если это служебный чат, AI не отвечает
        except (ValueError, TypeError):
            logging.warning("Не удалось проверить chat_id. AI может работать во всех чатах.")
            pass
        # --- КОНЕЦ БЛОКИРОВКИ AI ---
        
        # --- РАБОТА В ГРУППОВЫХ ЧАТАХ ---
        is_group_chat = message.chat.type in ['group', 'supergroup']
        
        if is_group_chat:
            chat_title = message.chat.title or "Без названия"
            text_lower = message.text.lower() if message.text else ""
            
            # ПРИОРИТЕТ 0: Проактивные сообщения (РЕДКО!)
            proactive_response = proactive_messenger.should_respond(message.text, message.chat.id)
            if proactive_response:
                logging.info(f"🎲 Проактивный ответ в группе '{chat_title}'")
                bot.reply_to(message, proactive_response)
                return
            
            # ПРИОРИТЕТ 1: Ключевые слова для помощи (ВСЕГДА отвечаем!)
            # Бронирование
            booking_keywords = [
                'забронир', 'бронь', 'столик', 'резерв', 
                'стол', 'место', 'заказать стол'
            ]
            # Навигация и помощь
            navigation_keywords = [
                'что умеешь', 'что можешь', 'помощь', 'help',
                'как работа', 'как получить', 'как заказать', 'инструкция',
                'настойка', 'настойку', 'купон', 'талон', 'скидка', 'бонус',
                'друг', 'товарищ', 'реферал', 'привести', 'пригласить',
                'адрес', 'где находи', 'как доехать', 'время работы', 'график',
                'цена', 'цены', 'стоимость', 'сколько стоит'
            ]
            
            has_booking_keyword = any(keyword in text_lower for keyword in booking_keywords)
            has_navigation_keyword = any(keyword in text_lower for keyword in navigation_keywords)
            
            # Если есть любое ключевое слово - отвечаем
            has_keyword = has_booking_keyword or has_navigation_keyword
            
            # Если есть любое ключевое слово - отвечаем
            has_keyword = has_booking_keyword or has_navigation_keyword
            
            if has_keyword:
                logging.info(f"✅ Группа '{chat_title}' ({message.chat.id}): КЛЮЧЕВОЕ СЛОВО найдено в '{message.text[:50]}'")
                # Установим флаг что нужна кнопка бронирования только если это про бронь
                message.should_attach_booking_button = has_booking_keyword
                # Продолжаем обработку AI
            else:
                message.should_attach_booking_button = False
                # ПРИОРИТЕТ 2: Проверяем упоминание или reply
                bot_mentioned = False
                
                # Проверяем упоминание по @username
                if message.text and '@evgenichspbbot' in message.text.lower():
                    bot_mentioned = True
                    logging.info(f"✅ Группа '{chat_title}': УПОМИНАНИЕ @evgenichspbbot")
                
                # Проверяем reply на сообщение бота
                if message.reply_to_message and message.reply_to_message.from_user.is_bot:
                    bot_mentioned = True
                    logging.info(f"✅ Группа '{chat_title}': REPLY на бота")
                
                # Проверяем entities (mentions)
                if message.entities:
                    for entity in message.entities:
                        if entity.type == 'mention':
                            mention_text = message.text[entity.offset:entity.offset + entity.length]
                            if 'evgenichspbbot' in mention_text.lower():
                                bot_mentioned = True
                                logging.info(f"✅ Группа '{chat_title}': УПОМИНАНИЕ через entity")
                                break
                
                # Если бот не упомянут, не отвечаем (для всех, включая админов)
                if not bot_mentioned:
                    logging.debug(f"⏭️  Группа '{chat_title}': пропуск - '{message.text[:30] if message.text else ''}'")
                    return
        # --- КОНЕЦ БЛОКА ГРУППОВЫХ ЧАТОВ ---

        user_id = message.from_user.id
        user_text = message.text
        
        # Инициализируем флаг кнопки, если его нет (для случаев без ключевых слов)
        if is_group_chat and not hasattr(message, 'should_attach_booking_button'):
            message.should_attach_booking_button = False

        # Список кнопок, которые обрабатываются в других хендлерах
        # ВАЖНО: '🗣 Спроси у Евгенича' убрана отсюда - она обрабатывается отдельным хендлером выше!
        known_buttons = [
            '🎁 Карта лояльности', '⭐ Оставить отзыв',
            '🥃 Получить настойку по талону', '📍 Забронировать стол', 
            '👑 Админка', '📨 Отправить БРОНЬ'
        ]
        # Изменение: убираем проверку на /admin, так как она теперь по тексту кнопки
        if user_text.startswith('/') or user_text in known_buttons:
            return

        logging.info(f"Пользователь {user_id} отправил текстовый запрос AI: '{user_text}'")
        
        try:
            # Определяем намерение пользователя
            intent = detect_intent(user_text)
            emotion = detect_emotion(user_text)
            
            logging.info(f"🎯 Намерение: {intent['intent']} (уверенность: {intent['confidence']})")
            logging.info(f"😊 Эмоция: {emotion['emotion']} (интенсивность: {emotion['intensity']})")
            
            # Обработка специальных намерений
            if intent['confidence'] > 0.5:
                # Локация
                if intent['intent'] == 'location':
                    locations = get_location_info()
                    location_text = "📍 **Наши адреса:**\n\n"
                    for bar_id, info in locations.items():
                        location_text += f"**{info['name']}**\n"
                        location_text += f"📍 {info['address']}\n"
                        location_text += f"🚇 Метро: {info['metro']}\n"
                        location_text += f"📞 {info['phone']}\n\n"
                    bot.send_message(message.chat.id, location_text, parse_mode="Markdown")
                    return
                
                # Часы работы
                elif intent['intent'] == 'hours':
                    hours_text = f"🕐 **Режим работы:**\n{get_working_hours()}\n\n"
                    bar_context = get_current_bar_context()
                    if bar_context['is_open']:
                        hours_text += "✅ Сейчас мы открыты! Приходи!"
                    else:
                        hours_text += "❌ Сейчас мы закрыты. Приходи после 12:00!"
                    bot.send_message(message.chat.id, hours_text, parse_mode="Markdown")
                    return
                
                # Бронирование
                elif intent['intent'] == 'booking':
                    # В группах - генерируем персональный ответ через AI и отправляем кнопку
                    # В личке - открываем форму
                    if is_group_chat:
                        logging.info(f"📍 Бронирование в группе (детектор намерений) - генерирую персональный ответ через AI")
                        # Устанавливаем флаг что нужна кнопка
                        message.should_attach_booking_button = True
                        # НЕ возвращаемся здесь - пусть AI сгенерирует персональный ответ
                        # После ответа AI добавим кнопку
                    else:
                        # В личке открываем форму
                        bot.send_message(
                            message.chat.id,
                            texts.BOOKING_PROMPT_TEXT,
                            reply_markup=keyboards.get_booking_options_keyboard()
                        )
                        return
                
                # Жалоба - уведомить администраторов
                elif intent['intent'] == 'complaint':
                    complaint_text = f"⚠️ **Жалоба от гостя**\n\n"
                    complaint_text += f"👤 User ID: {user_id}\n"
                    complaint_text += f"📝 Сообщение: {user_text}\n"
                    # Отправляем администраторам
                    for admin_id in ALL_ADMINS:
                        try:
                            bot.send_message(admin_id, complaint_text, parse_mode="Markdown")
                        except:
                            pass
                    logging.warning(f"⚠️ Получена жалоба от пользователя {user_id}: {user_text}")
            
            # Логируем диалог
            database.log_conversation_turn(user_id, "user", user_text)
            
            # Извлекаем предпочтения из текста
            extract_preferences_from_text(user_id, user_text)
            preferences_text = get_preferences_text(user_id)

            # Улучшенная история диалога - 12 сообщений для лучшего контекста
            history = database.get_conversation_history(user_id, limit=12)
            daily_updates = database.get_daily_updates()
            
            # Получаем выбранную пользователем концепцию
            user_concept = database.get_user_concept(user_id)
            
            # Получаем информацию о пользователе для персонализации
            user_info = database.find_user_by_id(user_id)
            visits_count = 0  # Визиты пока не отслеживаются в БД
            user_type = analyze_user_type(user_info, visits_count)
            
            # Получаем контекст бара
            bar_context = get_current_bar_context()
            bar_info = get_bar_info_text(bar_context)

            bot.send_chat_action(message.chat.id, 'typing')

            ai_response = get_ai_recommendation(
                user_query=user_text,
                conversation_history=history,
                user_id=user_id,  # НОВОЕ: передаём user_id для контекста и метрик
                daily_updates=daily_updates,
                user_concept=user_concept,
                user_type=user_type,
                bar_context=bar_info,
                emotion=emotion,
                preferences=preferences_text,
                is_group_chat=is_group_chat
            )

            database.log_conversation_turn(user_id, "assistant", ai_response)

            if "[START_BOOKING_FLOW]" in ai_response:
                logging.info(f"AI определил намерение бронирования для пользователя {user_id}.")
                
                # Убираем маркер из текста, но оставляем остальное сообщение
                clean_text = ai_response.replace("[START_BOOKING_FLOW]", "").strip()
                
                # Если есть текст перед маркером - отправляем его
                if clean_text:
                    bot.send_message(message.chat.id, clean_text, parse_mode="Markdown")
                
                # Отправляем кнопки бронирования
                bot.send_message(
                    message.chat.id,
                    texts.BOOKING_PROMPT_TEXT,
                    reply_markup=keyboards.get_booking_options_keyboard()
                )
            else:
                try:
                    # Проверяем нужна ли кнопка бронирования в ГРУППЕ
                    booking_button = None
                    
                    # Если это группа И (намерение booking ИЛИ есть ключевое слово бронирования)
                    should_book = getattr(message, 'should_attach_booking_button', False)
                    intent_is_booking = intent.get('intent') == 'booking' and intent.get('confidence', 0) > 0.5
                    
                    if is_group_chat and (intent_is_booking or should_book):
                        booking_button = keyboards.get_quick_booking_button()
                        logging.info(f"📍 Прикрепляю кнопку бронирования к ответу AI в группе (intent: {intent.get('intent')}, keyword: {should_book})")
                    
                    # Отправляем ответ AI с кнопкой (если нужно)
                    sent_message = bot.reply_to(message, ai_response, parse_mode="Markdown", reply_markup=booking_button)
                    
                except ApiTelegramException as e:
                    if "can't parse entities" in e.description:
                        logging.warning(f"Ошибка парсинга Markdown. Отправляю без форматирования. Текст: {ai_response}")
                        
                        # Проверяем нужна ли кнопка бронирования в ГРУППЕ (при ошибке парсинга)
                        booking_button = None
                        should_book = getattr(message, 'should_attach_booking_button', False)
                        intent_is_booking = intent.get('intent') == 'booking' and intent.get('confidence', 0) > 0.5
                        if is_group_chat and (intent_is_booking or should_book):
                            booking_button = keyboards.get_quick_booking_button()
                        
                        sent_message = bot.reply_to(message, ai_response, parse_mode=None, reply_markup=booking_button)
                    else:
                        logging.error(f"Неизвестная ошибка Telegram API при отправке ответа AI: {e}")
        
        except Exception as e:
            logging.error(f"❌ Критическая ошибка в AI обработчике для пользователя {user_id}: {e}", exc_info=True)
            try:
                bot.reply_to(message, "Товарищ, произошла техническая заминка 🔧 Попробуй ещё раз через пару секунд!")
            except:
                pass
