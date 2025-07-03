# main.py
import telebot
import logging

# Импортируем все необходимое из наших модулей
from config import BOT_TOKEN
from handlers import register_handlers
from database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Инициализация бота
# parse_mode="Markdown" можно убрать, если вы не используете markdown-разметку в ответах
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# === Точка входа ===
if __name__ == "__main__":
    logging.info("Инициализация базы данных...")
    init_db()
    
    logging.info("Регистрация обработчиков...")
    register_handlers(bot)
    
    logging.info("🚀 Бот запущен и готов к работе.")
    bot.infinity_polling()
