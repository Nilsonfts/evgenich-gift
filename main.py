# main.py

import telebot
import logging
import os

from config import BOT_TOKEN

from handlers.user_commands import register_user_command_handlers
from handlers.callback_query import register_callback_handlers
from handlers.booking_flow import register_booking_handlers
from handlers.admin_panel import register_admin_handlers
from handlers.ai_logic import register_ai_handlers

# Убедимся, что папка для логов существует
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

if __name__ == "__main__":
    logging.info("🤖 Начинаю регистрацию обработчиков...")

    # Регистрируем обработчики команд, кнопок и админки
    register_user_command_handlers(bot)
    register_callback_handlers(bot)
    register_admin_handlers(bot)
    
    # --- ИСПРАВЛЕНИЕ: Порядок важен! ---
    # Сначала регистрируем обработчик бронирования, который будет перехватывать сообщения, если пользователь в процессе.
    register_booking_handlers(bot)
    
    # И только потом регистрируем обработчик AI, который будет ловить все остальные текстовые сообщения.
    register_ai_handlers(bot)
    
    logging.info("✅ Все обработчики успешно зарегистрированы.")
    logging.info("🚀 Бот запущен и готов к работе.")
    
    # Запускаем бота с пропуском старых сообщений, которые могли прийти, пока бот был выключен
    bot.infinity_polling(skip_pending=True)
