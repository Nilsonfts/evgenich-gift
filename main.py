# main.py

import telebot
import logging
import os

# --- Конфигурация ---
from config import BOT_TOKEN

# --- Импорт регистраторов из наших новых модулей ---
from handlers.user_commands import register_user_command_handlers
from handlers.callback_query import register_callback_handlers
from handlers.booking_flow import register_booking_handlers
from handlers.admin_panel import register_admin_handlers
from handlers.ai_logic import register_ai_handlers

# --- Настройка логирования ---
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

# --- Инициализация бота ---
# parse_mode="Markdown" здесь можно убрать, так как мы указываем его в каждом сообщении
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)


# === Точка входа в приложение ===
if __name__ == "__main__":
    logging.info("🤖 Начинаю регистрацию обработчиков...")

    # Регистрируем все обработчики из наших модулей
    register_user_command_handlers(bot)
    register_callback_handlers(bot)
    register_booking_handlers(bot)
    register_admin_handlers(bot)
    
    # AI-обработчик должен быть последним, так как он ловит весь остальной текст
    register_ai_handlers(bot)
    
    logging.info("✅ Все обработчики успешно зарегистрированы.")
    logging.info("🚀 Бот запущен и готов к работе.")
    
    # Запускаем бота
    bot.infinity_polling(skip_pending=True)
