# /handlers/ai_logic.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from tinydb import TinyDB, Query

from ai.assistant import get_ai_recommendation
import database
import texts
import keyboards
from config import REPORT_CHAT_ID, NASTOYKA_NOTIFICATIONS_CHAT_ID, BOOKING_NOTIFICATIONS_CHAT_ID  # <--- ИЗМЕНЕНИЕ: Импортируем ID чатов для отчетов

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
        database.log_conversation_turn(user_id, "user", user_text)

        history = database.get_conversation_history(user_id, limit=6)
        daily_updates = database.get_daily_updates()
        
        # Получаем выбранную пользователем концепцию
        user_concept = database.get_user_concept(user_id)

        bot.send_chat_action(message.chat.id, 'typing')

        ai_response = get_ai_recommendation(
            user_query=user_text,
            conversation_history=history,
            daily_updates=daily_updates,
            user_concept=user_concept  # Передаем концепцию в AI
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
