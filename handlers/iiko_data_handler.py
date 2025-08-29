# handlers/iiko_data_handler.py
"""
Обработчик для получения данных из iiko.
"""
import datetime
import logging
import re
from telebot import types
from core.config import REPORT_CHAT_ID, NASTOYKA_NOTIFICATIONS_CHAT_ID, ALL_ADMINS
from core.database import save_iiko_nastoika_count, is_waiting_for_iiko_data
from texts import IIKO_DATA_RECEIVED_TEXT, IIKO_DATA_ERROR_TEXT

def register_iiko_data_handlers(bot):
    """Регистрирует обработчики для данных iiko."""
    
    @bot.message_handler(func=lambda message: (
        message.chat.id == NASTOYKA_NOTIFICATIONS_CHAT_ID and
        message.from_user.id in ALL_ADMINS and
        message.text and
        message.text.isdigit() and
        is_waiting_for_iiko_data(datetime.date.today())
    ))
    def handle_iiko_data_input(message):
        """Обрабатывает ввод данных по настойкам из iiko."""
        try:
            nastoika_count = int(message.text.strip())
            report_date = datetime.date.today()
            
            # Сохраняем данные
            success = save_iiko_nastoika_count(
                report_date=report_date,
                nastoika_count=nastoika_count,
                reported_by_user_id=message.from_user.id
            )
            
            if success:
                bot.reply_to(message, IIKO_DATA_RECEIVED_TEXT)
                logging.info(f"Получены данные iiko: {nastoika_count} настоек за {report_date} от пользователя {message.from_user.id}")
            else:
                bot.reply_to(message, "❌ Ошибка сохранения данных. Попробуйте еще раз.")
                
        except ValueError:
            bot.reply_to(message, IIKO_DATA_ERROR_TEXT)
        except Exception as e:
            logging.error(f"Ошибка обработки данных iiko: {e}")
            bot.reply_to(message, "❌ Произошла ошибка при обработке данных.")
    
    logging.info("Обработчики данных iiko зарегистрированы")
