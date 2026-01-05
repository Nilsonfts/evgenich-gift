"""
Обработчики для кнопки бронирования в групповом чате
"""

import logging
from telebot import types
from core.admin_config import get_staff


def register_chat_booking_handlers(bot):
    """Регистрирует обработчики для кнопки бронирования в чате"""
    
    @bot.message_handler(commands=['pin_booking'])
    def pin_booking_button(message):
        """Создает и закрепляет кнопку бронирования в чате"""
        
        logging.info(f"📌 ПОЛУЧЕНА команда /pin_booking от пользователя {message.from_user.id} ({message.from_user.first_name}) в чате {message.chat.id}")
        logging.info(f"🔍 Тип чата: {message.chat.type}")
        
        try:
            # Получаем список боссов из админ-конфига
            staff = get_staff()
            boss_ids = [boss['id'] for boss in staff.get('bosses', [])]
            
            logging.info(f"🔑 Список боссов из админ-конфига: {boss_ids}")
            logging.info(f"👤 User ID: {message.from_user.id}")
            
            # Если список пустой, разрешаем всем (для теста)
            if not boss_ids:
                logging.warning("⚠️ Список боссов пуст! Разрешаем команду всем")
                is_boss = True
            else:
                is_boss = message.from_user.id in boss_ids
                
            if not is_boss:
                bot.reply_to(message, "❌ У вас нет прав на эту команду")
                logging.warning(f"❌ Отказано в доступе пользователю {message.from_user.id}. Боссы: {boss_ids}")
                return
            
            # Создаем сообщение с кнопкой
            text = "📍Столик у Евгенича"
            
            markup = types.InlineKeyboardMarkup()
            
            # Кнопка переводит в ЛС бота с параметром booking
            booking_button = types.InlineKeyboardButton(
                text="ЗАБРОНИРОВАТЬ🍷",
                url="https://t.me/evgenichspbbot?start=booking"
            )
            
            markup.add(booking_button)
            
            # Отправляем сообщение
            msg = bot.send_message(
                message.chat.id,
                text,
                parse_mode='HTML',
                reply_markup=markup
            )
            
            # Пробуем закрепить сообщение в чате
            try:
                bot.pin_chat_message(message.chat.id, msg.message_id)
                bot.reply_to(message, "✅ Кнопка бронирования закреплена в чате!")
                logging.info(f"✅ Кнопка бронирования закреплена в чате {message.chat.id}, сообщение {msg.message_id}")
            except Exception as pin_error:
                bot.reply_to(message, f"✅ Кнопка создана, но не удалось закрепить: {str(pin_error)}")
                logging.warning(f"⚠️ Не удалось закрепить сообщение: {str(pin_error)}")
                
        except Exception as e:
            bot.reply_to(message, f"❌ Общая ошибка: {str(e)}")
            logging.error(f"❌ Ошибка в pin_booking_button: {str(e)}", exc_info=True)
    
    # Добавляем простой тестовый обработчик
    @bot.message_handler(commands=['test_chat'])
    def test_chat_command(message):
        """Простой тест что бот работает в чате"""
        logging.info(f"🧪 Тестовая команда от {message.from_user.id} в чате {message.chat.id}")
        logging.info(f"🔍 Тип чата: {message.chat.type}")
        bot.reply_to(message, f"🤖 Бот работает! Chat ID: {message.chat.id}, Type: {message.chat.type}")

    # Обработчик для текстовых сообщений с ключевыми словами в группах
    @bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'] and 
                         message.text and 
                         ('закрепить' in message.text.lower() and 'бронирование' in message.text.lower()) or
                         ('pin booking' in message.text.lower()))
    def pin_booking_text(message):
        """Альтернативный способ для групп - через текст"""
        logging.info(f"📌 ПОЛУЧЕН текстовый запрос на закрепление от {message.from_user.id} в группе {message.chat.id}")
        pin_booking_button(message)  # Вызываем основную функцию
        
    logging.info("✅ Обработчики для групповых чатов зарегистрированы")


