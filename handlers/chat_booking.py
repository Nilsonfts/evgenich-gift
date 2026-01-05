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
        
        logging.info(f"📌 Команда /pin_booking от пользователя {message.from_user.id} в чате {message.chat.id}")
        
        # Получаем список боссов из админ-конфига
        staff = get_staff()
        boss_ids = [boss['id'] for boss in staff.get('bosses', [])]
        
        logging.info(f"🔑 Список боссов из админ-конфига: {boss_ids}")
        logging.info(f"👤 User ID: {message.from_user.id}")
        
        # Если список пустой, разрешаем всем
        if not boss_ids:
            logging.warning("⚠️ Список боссов пуст! Разрешаем команду всем")
        elif message.from_user.id not in boss_ids:
            bot.reply_to(message, "❌ У вас нет прав на эту команду")
            logging.warning(f"❌ Отказано в доступе пользователю {message.from_user.id}. Боссы: {boss_ids}")
            return
        
        # Создаем сообщение с кнопкой
        text = "🍷 <b>Забронировать столик в Евгенич</b>\n\nНажмите кнопку ниже, чтобы открыть форму бронирования"
        
        markup = types.InlineKeyboardMarkup()
        
        # Кнопка переводит в ЛС бота с параметром booking
        booking_button = types.InlineKeyboardButton(
            text="📍 Забронировать столик",
            url="https://t.me/EvgenichBarBot?start=booking"
        )
        
        markup.add(booking_button)
        
        try:
            # Отправляем сообщение
            msg = bot.send_message(
                message.chat.id,
                text,
                parse_mode='HTML',
                reply_markup=markup
            )
            
            # Закрепляем сообщение в чате
            bot.pin_chat_message(message.chat.id, msg.message_id)
            bot.reply_to(message, "✅ Кнопка бронирования закреплена в чате!")
            logging.info(f"✅ Кнопка бронирования закреплена в чате {message.chat.id}, сообщение {msg.message_id}")
            
        except Exception as e:
            bot.reply_to(message, f"⚠️ Ошибка при закреплении: {str(e)}")
            logging.error(f"❌ Ошибка при закреплении кнопки: {str(e)}")


