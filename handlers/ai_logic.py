# /handlers/ai_logic.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from tinydb import TinyDB, Query

from ai.assistant import get_ai_recommendation
from ai.intent_recognition import detect_intent, detect_emotion, analyze_user_type
from ai.bar_context import get_current_bar_context, get_bar_info_text, get_location_info, get_working_hours
from ai.user_preferences import extract_preferences_from_text, get_preferences_text
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
        # В группах проверяем упоминание ТОЛЬКО если это НЕ вопрос о бронировании
        is_group_chat = message.chat.type in ['group', 'supergroup']
        
        if is_group_chat:
            # Сначала проверяем, не вопрос ли это о бронировании
            text_lower = message.text.lower() if message.text else ""
            booking_keywords = ['забронир', 'бронь', 'столик', 'резерв', 'стол']
            is_booking_question = any(keyword in text_lower for keyword in booking_keywords)
            
            # Если это вопрос о бронировании - отвечаем всегда
            if is_booking_question:
                logging.info(f"📍 Вопрос о бронировании в группе {message.chat.id}, отвечаем!")
            else:
                # Для остальных вопросов проверяем упоминание
                bot_mentioned = False
                
                # Проверяем упоминание по @username
                if message.text and '@evgenichspbbot' in message.text.lower():
                    bot_mentioned = True
                
                # Проверяем reply на сообщение бота
                if message.reply_to_message and message.reply_to_message.from_user.is_bot:
                    bot_mentioned = True
                
                # Проверяем entities (mentions)
                if message.entities:
                    for entity in message.entities:
                        if entity.type == 'mention':
                            mention_text = message.text[entity.offset:entity.offset + entity.length]
                            if 'evgenichspbbot' in mention_text.lower():
                                bot_mentioned = True
                                break
                
                # Если бот не упомянут, не отвечаем
                if not bot_mentioned:
                    logging.info(f"Сообщение в группе {message.chat.id}, но бот не упомянут - игнорируем")
                    return
                
                logging.info(f"Бот упомянут в группе {message.chat.id}, отвечаем!")
        # --- КОНЕЦ БЛОКА ГРУППОВЫХ ЧАТОВ ---

        user_id = message.from_user.id
        user_text = message.text

        known_buttons = [
            '📖 Меню', '🤝 Привести товарища', '🗣 Спроси у Евгенича',
            '🥃 Получить настойку по талону', '📍 Забронировать стол', 
            '👑 Админка', '📨 Отправить БРОНЬ'
        ]
        # Изменение: убираем проверку на /admin, так как она теперь по тексту кнопки
        if user_text.startswith('/') or user_text in known_buttons:
            return

        logging.info(f"Пользователь {user_id} отправил текстовый запрос AI: '{user_text}'")
        
        # Определяем намерение пользователя
        intent = detect_intent(user_text)
        emotion = detect_emotion(user_text)
        
        logging.info(f"🎯 Намерение: {intent['intent']} (уверенность: {intent['confidence']})")
        logging.info(f"😊 Эмоция: {emotion['emotion']} (интенсивность: {emotion['intensity']})")
        
        # Обработка специальных намерений
        if intent['confidence'] > 0.5:
            # Меню
            if intent['intent'] == 'menu':
                bot.send_message(
                    message.chat.id,
                    "📖 Вот наше меню! Выбирай что душа просит:",
                    reply_markup=keyboards.get_main_menu_keyboard(user_id)
                )
                return
            
            # Локация
            elif intent['intent'] == 'location':
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
                # В группах - направляем на закрепленную кнопку через AI
                # В личке - открываем форму
                if is_group_chat:
                    logging.info(f"📍 Бронирование в группе - направляем на кнопку через AI")
                    # НЕ открываем форму, пусть AI ответит и направит на кнопку
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
        visits_count = len(database.get_user_visits(user_id)) if user_info else 0
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
            bot.send_message(
                message.chat.id,
                texts.BOOKING_PROMPT_TEXT,
                reply_markup=keyboards.get_booking_options_keyboard()
            )
        else:
            try:
                bot.reply_to(message, ai_response, parse_mode="Markdown")
            except ApiTelegramException as e:
                if "can't parse entities" in e.description:
                    logging.warning(f"Ошибка парсинга Markdown. Отправляю без форматирования. Текст: {ai_response}")
                    bot.reply_to(message, ai_response, parse_mode=None)
                else:
                    logging.error(f"Неизвестная ошибка Telegram API при отправке ответа AI: {e}")
