# main.py

import telebot
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import pytz

from config import BOT_TOKEN, FRIEND_BONUS_STICKER_ID, REPORT_CHAT_ID, CHANNEL_ID
import database
import keyboards
import texts

from handlers.user_commands import register_user_command_handlers
from handlers.callback_query import register_callback_handlers
from handlers.booking_flow import register_booking_handlers
from handlers.admin_panel import register_admin_handlers, send_report
from handlers.ai_logic import register_ai_handlers
from handlers.iiko_data_handler import register_iiko_data_handlers
from delayed_tasks_processor import DelayedTasksProcessor

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
delayed_tasks_processor = DelayedTasksProcessor(bot)

def send_friend_bonus(referrer_id, friend_name):
    # Тут должна быть ваша логика отправки бонуса
    pass

def request_feedback(user_id):
    # Тут должна быть ваша логика запроса обратной связи
    pass

def send_daily_report_job():
    """Формирует и отправляет отчет за смену с 12:00 до 06:00."""
    logging.info("Scheduler: Запускаю отправку ежедневного отчета...")
    try:
        tz_moscow = pytz.timezone('Europe/Moscow')
        current_time = datetime.datetime.now(tz_moscow)
        
        # Если сейчас до 12:00, то отчет за смену: 12:00 позавчера - 06:00 вчера
        # Если сейчас после 12:00, то отчет за смену: 12:00 вчера - 06:00 сегодня
        if current_time.hour < 12:
            # Отчет за позавчерашнюю смену
            end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            # Отчет за вчерашнюю смену  
            end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            if current_time.hour >= 6:
                # Если сейчас после 06:00, то берем сегодняшние 06:00
                pass
            else:
                # Если сейчас до 06:00, то берем вчерашние 06:00
                end_time = end_time - datetime.timedelta(days=1)
            start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        
        logging.info(f"Формирую отчет за смену: {start_time.strftime('%d.%m.%Y %H:%M')} - {end_time.strftime('%d.%m.%Y %H:%M')}")
        
        # Запрашиваем данные iiko перед отправкой отчета
        report_date = end_time.date()
        request_iiko_data_before_report(report_date, start_time, end_time)
        
    except Exception as e:
        logging.error(f"Scheduler: Ошибка при отправке ежедневного отчета: {e}")

def request_iiko_data_before_report(report_date: datetime.date, start_time: datetime.datetime, end_time: datetime.datetime):
    """Запрашивает данные iiko перед формированием отчета."""
    from texts import IIKO_DATA_REQUEST_TEXT
    from database import is_waiting_for_iiko_data
    
    # Проверяем, нужны ли данные за эту дату
    if is_waiting_for_iiko_data(report_date):
        try:
            # Отправляем запрос в чат отчетов в 05:30
            bot.send_message(
                REPORT_CHAT_ID,
                IIKO_DATA_REQUEST_TEXT,
                parse_mode='Markdown'
            )
            logging.info(f"Отправлен запрос данных iiko за {report_date}")
            
            # Планируем отправку отчета через 35 минут (в 06:05)
            scheduler.add_job(
                lambda: send_final_report_with_iiko(start_time, end_time),
                'date',
                run_date=datetime.datetime.now(pytz.timezone('Europe/Moscow')) + datetime.timedelta(minutes=35),
                id=f'final_report_{report_date}',
                replace_existing=True
            )
            
        except Exception as e:
            logging.error(f"Ошибка запроса данных iiko: {e}")
            # Если не удалось запросить, отправляем отчет без данных iiko
            send_final_report_with_iiko(start_time, end_time)
    else:
        # Данные уже есть, отправляем отчет сразу
        send_final_report_with_iiko(start_time, end_time)

def send_final_report_with_iiko(start_time: datetime.datetime, end_time: datetime.datetime):
    """Отправляет финальный отчет с данными iiko (если есть)."""
    try:
        send_report(bot, REPORT_CHAT_ID, start_time, end_time)
        logging.info(f"Scheduler: Ежедневный отчет успешно отправлен в чат {REPORT_CHAT_ID}.")
    except Exception as e:
        logging.error(f"Ошибка отправки финального отчета: {e}")

def run_nightly_auditor_job():
    """
    Проверяет всех, кто погасил купон, на наличие подписки.
    """
    logging.info("Аудитор: Начинаю ночную проверку отписавшихся...")
    users_to_check = database.get_redeemed_users_for_audit()
    if not users_to_check:
        logging.info("Аудитор: Нет пользователей для проверки. Завершаю.")
        return

    logging.info(f"Аудитор: Найдено {len(users_to_check)} пользователей для проверки.")
    left_count = 0
    for user_row in users_to_check:
        user_id = user_row['user_id']
        try:
            # Делаем паузу, чтобы не превышать лимиты Telegram
            import time
            time.sleep(1)
            
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                # Пользователь отписался
                database.mark_user_as_left(user_id)
                left_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            if 'user not found' in e.description or 'bot was blocked by the user' in e.description:
                # Пользователь удалил аккаунт или заблокировал бота
                database.mark_user_as_left(user_id)
                left_count += 1
                logging.warning(f"Аудитор: Пользователь {user_id} не найден (удалил/заблокировал). Помечен как отписавшийся.")
            else:
                logging.error(f"Аудитор: Ошибка API Telegram при проверке {user_id}: {e}")
        except Exception as e:
            logging.error(f"Аудитор: Неизвестная ошибка при проверке {user_id}: {e}")

    logging.info(f"Аудитор: Проверка завершена. Найдено {left_count} отписавшихся.")

if __name__ == "__main__":
    logging.info("🔧 Инициализация базы данных...")
    database.init_db()

    logging.info("🤖 Начинаю регистрацию обработчиков...")
    register_user_command_handlers(bot)
    register_callback_handlers(bot, scheduler, send_friend_bonus, request_feedback)
    register_booking_handlers(bot)
    register_admin_handlers(bot)
    register_ai_handlers(bot)
    register_iiko_data_handlers(bot)

    # Ежедневный отчет в 05:30 (запрос данных iiko)
    scheduler.add_job(
        send_daily_report_job,
        trigger=CronTrigger(hour=5, minute=30, timezone='Europe/Moscow'),
        id='daily_report_job', name='Daily report', replace_existing=True
    )
    logging.info("Scheduler: Задача для ежедневного отчета запланирована на 05:30.")

    # Ночной аудитор в 04:00
    scheduler.add_job(
        run_nightly_auditor_job,
        trigger=CronTrigger(hour=4, minute=0, timezone='Europe/Moscow'),
        id='nightly_auditor_job', name='Nightly Auditor', replace_existing=True
    )
    logging.info("Scheduler: Задача 'Ночной Аудитор' запланирована на 04:00.")

    scheduler.start()
    delayed_tasks_processor.start()
    logging.info("✅ Все обработчики, планировщик и обработчик отложенных задач успешно запущены.")

    bot.infinity_polling(skip_pending=True)
