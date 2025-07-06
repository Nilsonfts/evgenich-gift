# main.py

import telebot
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler

from config import BOT_TOKEN, FRIEND_BONUS_STICKER_ID
import database  # <--- ИЗМЕНЕНИЕ: импортируем database вместо g_sheets
import keyboards
import texts

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
scheduler = BackgroundScheduler(timezone="Europe/Moscow")

# --- Функции для отложенных задач ---
def send_friend_bonus(referrer_id, friend_name):
    try:
        bot.send_message(referrer_id, f"🤝 Товарищ! Ваш друг {friend_name} успешно получил настойку. А это — ваш честно заработанный бонус! Поздравляем!")
        bot.send_sticker(referrer_id, FRIEND_BONUS_STICKER_ID)
        bot.send_message(referrer_id, "Покажите это сообщение бармену, чтобы получить свой подарок.", reply_markup=keyboards.get_redeem_keyboard())
        logging.info(f"Бонус за друга успешно отправлен рефереру {referrer_id}.")
    except Exception as e:
        logging.error(f"Не удалось отправить бонус рефереру {referrer_id}: {e}")

def request_feedback(user_id):
    from telebot import types
    try:
        feedback_keyboard = types.InlineKeyboardMarkup()
        buttons = [types.InlineKeyboardButton(text=f"{'⭐'*i}", callback_data=f"feedback_{i}") for i in range(1, 6)]
        feedback_keyboard.row(*buttons)
        bot.send_message(user_id, texts.FEEDBACK_PROMPT, reply_markup=feedback_keyboard)
        logging.info(f"Запрос на обратную связь отправлен пользователю {user_id}.")
    except Exception as e:
        logging.error(f"Не удалось отправить запрос на ОС пользователю {user_id}: {e}")

if __name__ == "__main__":
    logging.info("🔧 Инициализация базы данных...")
    database.init_db()  # <--- ВАЖНО: создаем БД и таблицы перед запуском

    logging.info("🤖 Начинаю регистрацию обработчиков...")

    register_user_command_handlers(bot)
    register_callback_handlers(bot, scheduler, send_friend_bonus, request_feedback)
    register_booking_handlers(bot)
    register_admin_handlers(bot)
    register_ai_handlers(bot)
    
    scheduler.start()
    logging.info("✅ Все обработчики успешно зарегистрированы.")
    logging.info("🚀 Бот запущен и готов к работе.")
    
    bot.infinity_polling(skip_pending=True)
