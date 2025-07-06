# /handlers/ai_logic.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from tinydb import TinyDB, Query

from ai_assistant import get_ai_recommendation
import database  # <--- ИЗМЕНЕНИЕ
import texts
import keyboards

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
        user_id = message.from_user.id
        user_text = message.text

        known_buttons = [
            '📖 Меню', '🤝 Привести товарища', '🗣 Спроси у Евгенича',
            '🥃 Получить настойку по талону', '📍 Забронировать стол', '👑 /admin'
        ]
        if user_text.startswith('/') or user_text in known_buttons:
            return

        logging.info(f"Пользователь {user_id} отправил текстовый запрос AI: '{user_text}'")
        # ИЗМЕНЕНИЕ: Логируем в локальную БД
        database.log_conversation_turn(user_id, "user", user_text)

        # ИЗМЕНЕНИЕ: Получаем историю и данные из локальной БД
        history = database.get_conversation_history(user_id, limit=6)
        daily_updates = database.get_daily_updates()

        bot.send_chat_action(message.chat.id, 'typing')

        ai_response = get_ai_recommendation(
            user_query=user_text,
            conversation_history=history,
            daily_updates=daily_updates
        )
        
        # ИЗМЕНЕНИЕ: Логируем ответ AI в локальную БД
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
