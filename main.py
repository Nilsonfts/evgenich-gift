# main.py 

import telebot
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import pytz

from config import BOT_TOKEN, FRIEND_BONUS_STICKER_ID, REPORT_CHAT_ID
import database
import keyboards
import texts

from handlers.user_commands import register_user_command_handlers
from handlers.callback_query import register_callback_handlers
from handlers.booking_flow import register_booking_handlers
from handlers.admin_panel import register_admin_handlers, send_report
from handlers.ai_logic import register_ai_handlers

# Настройка логов... (код без изменений)
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
    pass # ... (код этой функции без изменений)

def request_feedback(user_id):
    pass# ... (код этой функции без изменений)

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ЕЖЕДНЕВНОГО ОТЧЕТА ---
def send_daily_report_job():
    """
    Формирует и отправляет отчет за последние 24 часа.
    """
    logging.info("Scheduler: Запускаю отправку ежедневного отчета...")
    try:
        # Устанавливаем временной диапазон: с 06:00 вчера до 06:00 сегодня
        tz_moscow = pytz.timezone('Europe/Moscow')
        end_time = datetime.datetime.now(tz_moscow).replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = end_time - datetime.timedelta(days=1)
        
        # Вызываем функцию отправки отчета из админ-панели
        send_report(bot, REPORT_CHAT_ID, start_time, end_time)
        logging.info(f"Scheduler: Ежедневный отчет успешно отправлен в чат {REPORT_CHAT_ID}.")
    except Exception as e:
        logging.error(f"Scheduler: Ошибка при отправке ежедневного отчета: {e}")

if __name__ == "__main__":
    logging.info("🔧 Инициализация базы данных...")
    database.init_db()

    logging.info("🤖 Начинаю регистрацию обработчиков...")

    register_user_command_handlers(bot)
    register_callback_handlers(bot, scheduler, send_friend_bonus, request_feedback)
    register_booking_handlers(bot)
    register_admin_handlers(bot)
    register_ai_handlers(bot)
    
    # --- ДОБАВЛЕНИЕ ЗАДАЧИ В ПЛАНИРОВЩИК ---
    scheduler.add_job(
        send_daily_report_job,
        trigger=CronTrigger(hour=6, minute=5, timezone='Europe/Moscow'), # Каждый день в 06:05
        id='daily_report_job',
        name='Daily report',
        replace_existing=True
    )
    logging.info("Scheduler: Задача для ежедневного отчета запланирована на 06:05.")
    
    scheduler.start()
    logging.info("✅ Все обработчики и планировщик успешно запущены.")
    
    bot.infinity_polling(skip_pending=True)
