# main.py
import telebot
import logging

from config import BOT_TOKEN
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
bot = telebot.TeleBot(BOT_TOKEN)

# === Точка входа ===
if __name__ == "__main__":
    logging.info("Инициализация базы данных...")
    init_db()
    
    logging.info("🚀 Бот запущен. Ожидание команд...")
    bot.infinity_polling()
