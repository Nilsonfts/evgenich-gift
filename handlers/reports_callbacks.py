# /handlers/reports_callbacks.py
"""
Callback-обработчики отчетов для админ-панели.
"""
import datetime
import pytz
import database
from handlers.reports import send_report

def handle_report_callbacks(bot, admin_states, settings_manager, keyboards, texts):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_report_'))
    def report_callback(call):
        action = call.data
        tz_moscow = pytz.timezone('Europe/Moscow')
        end_time = datetime.datetime.now(tz_moscow)
        if action == 'admin_report_manual_daily':
            start_time = end_time - datetime.timedelta(days=1)
            send_report(bot, call.message.chat.id, start_time, end_time)
        elif action == 'admin_report_source_funnel':
            start_time = end_time - datetime.timedelta(days=30)
            _, _, _, sources, _ = database.get_report_data_for_period(start_time, end_time)
            if not sources:
                bot.send_message(call.message.chat.id, "Нет данных по источникам за месяц.")
            else:
                text = f"🔬 Воронка по источникам (30 дней):\n"
                total = sum(sources.values())
                for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                    percent = round(count / total * 100, 1) if total else 0
                    text += f"• {src or 'Неизвестно'}: {count} ({percent}%)\n"
                bot.send_message(call.message.chat.id, text)
        elif action == 'admin_report_churn_by_source':
            start_time = end_time - datetime.timedelta(days=30)
            try:
                conn = database.get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT source, COUNT(*) as cnt FROM users WHERE redeem_date BETWEEN ? AND ? AND status = 'redeemed_and_left' GROUP BY source", (start_time, end_time))
                rows = cur.fetchall()
                conn.close()
                if not rows:
                    bot.send_message(call.message.chat.id, "Нет данных по оттоку за месяц.")
                else:
                    total = sum(row['cnt'] for row in rows)
                    text = f"📈 Анализ оттока по источникам (30 дней):\n"
                    for row in rows:
                        percent = round(row['cnt'] / total * 100, 1) if total else 0
                        text += f"• {row['source'] or 'Неизвестно'}: {row['cnt']} ({percent}%)\n"
                    bot.send_message(call.message.chat.id, text)
            except Exception as e:
                bot.send_message(call.message.chat.id, f"Ошибка при формировании отчёта: {e}")
        elif action == 'admin_report_activity_time':
            start_time = end_time - datetime.timedelta(days=30)
            try:
                conn = database.get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT strftime('%H', signup_date) as hour, COUNT(*) as cnt FROM users WHERE signup_date BETWEEN ? AND ? GROUP BY hour ORDER BY hour", (start_time, end_time))
                rows = cur.fetchall()
                conn.close()
                if not rows:
                    bot.send_message(call.message.chat.id, "Нет данных по активности гостей за месяц.")
                else:
                    text = f"🕒 Пики активности гостей (регистрация, 30 дней):\n"
                    for row in rows:
                        text += f"• {row['hour']}:00 — {row['cnt']}\n"
                    bot.send_message(call.message.chat.id, text)
            except Exception as e:
                bot.send_message(call.message.chat.id, f"Ошибка при формировании отчёта: {e}")
