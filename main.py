# main.py

import telebot
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import pytz

from core.config import BOT_TOKEN, FRIEND_BONUS_STICKER_ID, REPORT_CHAT_ID, CHANNEL_ID, NASTOYKA_NOTIFICATIONS_CHAT_ID, USE_POSTGRES, DATABASE_URL, DATABASE_PATH, get_channel_id_for_user
import core.database as database
import keyboards
import texts

from handlers.user_commands import register_user_command_handlers
from handlers.callback_query import register_callback_handlers
from handlers.booking_flow import register_booking_handlers
from handlers.admin_panel import register_admin_handlers, init_admin_handlers
from handlers.reports import send_report
from handlers.ai_logic import register_ai_handlers
from handlers.iiko_data_handler import register_iiko_data_handlers
from handlers.broadcast import register_broadcast_handlers
from handlers.chat_booking import register_chat_booking_handlers
from handlers.admin_content import register_content_handlers  # AI System v3.0
from handlers.proactive_commands import register_proactive_commands  # Проактивные сообщения
from core.delayed_tasks_processor import DelayedTasksProcessor

# Импортируем службу реферальных уведомлений
try:
    from utils.referral_notifications import start_referral_notification_service
    REFERRAL_NOTIFICATIONS_AVAILABLE = True
except ImportError:
    logging.warning("Модуль реферальных уведомлений недоступен")
    REFERRAL_NOTIFICATIONS_AVAILABLE = False

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

def check_database_connections():
    """Проверяет подключения к базам данных."""
    logging.info("🔍 Проверка подключений к базам данных...")
    
    # Проверка SQLite
    try:
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        sqlite_users = cur.fetchone()[0]
        conn.close()
        logging.info(f"✅ SQLite подключение OK. Пользователей: {sqlite_users}")
    except Exception as e:
        logging.error(f"❌ Ошибка SQLite: {e}")
    
    # Проверка PostgreSQL
    if USE_POSTGRES and DATABASE_URL:
        try:
            from db.postgres_client import PostgresClient
            pg_client = PostgresClient()
            logging.info("✅ PostgreSQL подключение проверено в конструкторе")
        except Exception as e:
            logging.error(f"❌ Ошибка PostgreSQL: {e}")
    else:
        logging.warning("⚠️  PostgreSQL не настроен (USE_POSTGRES=false или DATABASE_URL пуст)")

def request_feedback(user_id):
    """Запрашивает обратную связь у пользователя."""
    try:
        bot.send_message(user_id, texts.FEEDBACK_REQUEST_TEXT)
        logging.info(f"Отправлен запрос обратной связи пользователю {user_id}")
    except Exception as e:
        logging.error(f"Ошибка отправки запроса обратной связи пользователю {user_id}: {e}")

def manual_feedback_request():
    # Тут должна быть ваша логика запроса обратной связи
    pass

def send_daily_report_job():
    """Формирует и отправляет отчет за смену с 12:00 до 06:00."""
    logging.info("Scheduler: Запускаю отправку ежедневного отчета в 07:00...")
    try:
        tz_moscow = pytz.timezone('Europe/Moscow')
        current_time = datetime.datetime.now(tz_moscow)
        
        # Отчет за смену: 12:00 вчера - 06:00 сегодня
        end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        
        logging.info(f"Формирую отчет за смену: {start_time.strftime('%d.%m.%Y %H:%M')} - {end_time.strftime('%d.%m.%Y %H:%M')}")
        
        # Отправляем отчет сразу (данные iiko опциональны)
        send_final_report_with_iiko(start_time, end_time)
        
    except Exception as e:
        logging.error(f"Scheduler: Ошибка при отправке ежедневного отчета: {e}")

def send_final_report_with_iiko(start_time: datetime.datetime, end_time: datetime.datetime):
    """Отправляет финальный отчет с данными iiko (если есть)."""
    try:
        send_report(bot, NASTOYKA_NOTIFICATIONS_CHAT_ID, start_time, end_time)
        logging.info(f"Scheduler: Ежедневный отчет успешно отправлен в чат настоек {NASTOYKA_NOTIFICATIONS_CHAT_ID}.")
    except Exception as e:
        logging.error(f"Ошибка отправки финального отчета: {e}")
        # Fallback - отправляем в старый чат если новый недоступен
        try:
            send_report(bot, REPORT_CHAT_ID, start_time, end_time)
            logging.info(f"Финальный отчет отправлен в резервный чат {REPORT_CHAT_ID}")
        except Exception as fallback_error:
            logging.error(f"Ошибка отправки в резервный чат: {fallback_error}")

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
            
            # Определяем правильный канал для проверки на основе источника пользователя
            user_source = user_row.get('source', '')
            channel_to_check = get_channel_id_for_user(user_source)
            
            chat_member = bot.get_chat_member(chat_id=channel_to_check, user_id=user_id)
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
    # Проверка подключений к базам данных
    check_database_connections()
    
    # Исправление проблем PostgreSQL collation
    if USE_POSTGRES and DATABASE_URL:
        try:
            from core.fix_postgresql_collation import fix_postgresql_collation
            fix_postgresql_collation()
        except Exception as e:
            logging.warning(f"⚠️  Не удалось исправить PostgreSQL collation: {e}")
    
    # Информация о подключении к базе данных
    if USE_POSTGRES:
        logging.info("🔧 Инициализация PostgreSQL базы данных...")
        logging.info(f"📊 PostgreSQL URL: {DATABASE_URL.split('@')[-1] if DATABASE_URL else 'Не настроен'}")
    else:
        logging.info("🔧 Инициализация SQLite базы данных...")
        logging.info(f"📄 SQLite DB path: {DATABASE_PATH}")
    
    database.init_db()

    logging.info("🤖 Начинаю регистрацию обработчиков...")
    register_chat_booking_handlers(bot)  # ПЕРВЫМ - для групповых команд
    register_booking_handlers(bot)       # ВТОРЫМ - process_booking_step должен перехватывать текст раньше handle_profile_data_collection
    register_user_command_handlers(bot)
    register_callback_handlers(bot, scheduler, send_friend_bonus, request_feedback)
    # Инициализируем систему рассылок с планировщиком (ПЕРЕД admin catch-all)
    init_admin_handlers(bot, scheduler)
    register_admin_handlers(bot)
    register_content_handlers(bot)  # AI System v3.0 - управление контентом
    register_proactive_commands(bot)  # Проактивные команды для админа
    register_broadcast_handlers(bot)  # ПЕРЕД AI — чтобы broadcast_states ловили текст раньше
    register_ai_handlers(bot)  # AI catch-all — ПОСЛЕДНИМ среди message handlers
    register_iiko_data_handlers(bot)

    # Ежедневный отчет в 07:00
    scheduler.add_job(
        send_daily_report_job,
        trigger=CronTrigger(hour=7, minute=0, timezone='Europe/Moscow'),
        id='daily_report_job', name='Daily report', replace_existing=True
    )
    logging.info("Scheduler: Задача для ежедневного отчета запланирована на 07:00.")

    # Ночной аудитор в 04:00
    scheduler.add_job(
        run_nightly_auditor_job,
        trigger=CronTrigger(hour=4, minute=0, timezone='Europe/Moscow'),
        id='nightly_auditor_job', name='Nightly Auditor', replace_existing=True
    )
    logging.info("Scheduler: Задача 'Ночной Аудитор' запланирована на 04:00.")

    scheduler.start()
    delayed_tasks_processor.start()
    
    # Запускаем службу реферальных уведомлений
    if REFERRAL_NOTIFICATIONS_AVAILABLE:
        try:
            start_referral_notification_service()
            logging.info("✅ Служба реферальных уведомлений запущена")
        except Exception as e:
            logging.error(f"❌ Ошибка запуска службы реферальных уведомлений: {e}")
    else:
        logging.warning("⚠️ Служба реферальных уведомлений недоступна")
    
    logging.info("✅ Все обработчики, планировщик и сервисы успешно запущены.")

    # === КРИТИЧНО: Удаляем webhook ПЕРЕД стартом polling ===
    # Если webhook установлен (например от веб-панели), Telegram НЕ отдаёт
    # updates через polling — все кнопки перестают работать!
    import time
    logging.info("🔄 Удаляю webhook и очищаю очередь обновлений...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        logging.info("✅ Webhook удалён, pending updates сброшены")
    except Exception as e:
        logging.warning(f"⚠️ Ошибка удаления webhook: {e}")
    time.sleep(2)  # Даём Telegram время обработать удаление

    # Проверяем что webhook точно удалён
    try:
        webhook_info = bot.get_webhook_info()
        if webhook_info.url:
            logging.error(f"❌ Webhook ВСЁ ЕЩЁ активен: {webhook_info.url}")
            bot.delete_webhook(drop_pending_updates=True)
            time.sleep(2)
        else:
            logging.info("✅ Webhook не установлен — polling будет работать")
    except Exception as e:
        logging.warning(f"⚠️ Не удалось проверить webhook: {e}")

    # Запуск бота с обработкой ошибок
    # КРИТИЧНО: указываем allowed_updates с callback_query, иначе кнопки не работают!
    ALLOWED_UPDATES = ['message', 'callback_query', 'inline_query', 'chosen_inline_result',
                       'edited_message', 'channel_post', 'edited_channel_post',
                       'my_chat_member', 'chat_member', 'chat_join_request']
    while True:
        try:
            logging.info("🚀 Запуск бота (long polling)...")
            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=ALLOWED_UPDATES
            )
        except Exception as e:
            logging.error(f"❌ Ошибка в работе бота: {e}")
            logging.error(f"Тип ошибки: {type(e).__name__}")
            logging.info("🔄 Перезапуск бота через 5 секунд...")
            time.sleep(5)
