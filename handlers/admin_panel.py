# /handlers/admin_panel.py

import logging
import datetime
from telebot import types
from telebot.apihelper import ApiTelegramException
import pytz

from config import ADMIN_IDS
import database
import texts
import keyboards
import settings_manager
from export_to_sheets import do_export
from handlers.user_commands import issue_coupon
from handlers.reports import send_report, generate_daily_report_text
from handlers.utils import shorten_name
from handlers.reports_callbacks import handle_report_callbacks
from handlers.staff import handle_staff_callbacks
from handlers.users import handle_user_callbacks
from handlers.promotions import handle_promotions_callbacks
from handlers.content import handle_content_callbacks

# --- Функции генерации отчетов ---

def register_admin_handlers(bot):
    """Регистрирует все команды и колбэки для админ-панели."""
    admin_states = {}

    def is_admin(user_id):
        return user_id in ADMIN_IDS

    @bot.message_handler(func=lambda message: message.text == "👑 Админка")
    def handle_admin_command(message: types.Message):
        if not is_admin(message.from_user.id):
            return
        bot.send_message(
            message.chat.id, "👑 **Главное меню админ-панели**\n\nВыберите нужный раздел:",
            reply_markup=keyboards.get_admin_main_menu()
        )

    # --- Пошаговые обработчики для админ-функций ---

    def process_find_user_step(message: types.Message):
        admin_id = message.from_user.id
        if admin_states.get(admin_id) != 'awaiting_user_identifier':
            return
        
        identifier = message.text
        user_data = database.find_user_by_id_or_username(identifier)
        
        if user_data:
            status_map = {
                'registered': 'Зарегистрирован', 'issued': 'Купон выдан',
                'redeemed': 'Купон погашен', 'redeemed_and_left': 'Погасил и отписался'
            }
            status_ru = status_map.get(user_data['status'], user_data['status'])
            staff_name = "Нет"
            if user_data.get('brought_by_staff_id'):
                staff_info = database.find_staff_by_id(user_data['brought_by_staff_id'])
                if staff_info:
                    staff_name = staff_info['short_name']

            response = (f"👤 **Профиль пользователя:**\n\n"
                        f"**ID:** `{user_data['user_id']}`\n"
                        f"**Имя:** {user_data['first_name']}\n"
                        f"**Юзернейм:** @{user_data['username'] or 'Нет'}\n"
                        f"**Статус:** {status_ru}\n"
                        f"**Источник:** {user_data['source'] or 'Неизвестен'}\n"
                        f"**Пригласил:** {user_data['referrer_id'] or 'Никто'}\n"
                        f"**Привел сотрудник:** {staff_name}\n"
                        f"**Дата регистрации:** {user_data['signup_date'] or 'Нет данных'}\n"
                        f"**Дата погашения:** {user_data['redeem_date'] or 'Еще не погашен'}")
            bot.send_message(admin_id, response, parse_mode="Markdown")
        else:
            bot.send_message(admin_id, f"❌ Пользователь с идентификатором '{identifier}' не найден.")
        if admin_id in admin_states:
            del admin_states[admin_id]

    def process_issue_coupon_step(message: types.Message):
        admin_id = message.from_user.id
        if admin_states.get(admin_id) != 'awaiting_coupon_user_id':
            return
        user_id_str = message.text
        if not user_id_str.isdigit():
            bot.send_message(admin_id, "❌ ID пользователя должен быть числом. Попробуйте снова.")
            return
        user_id = int(user_id_str)
        user_data = database.find_user_by_id(user_id)
        if not user_data:
            bot.send_message(admin_id, f"❌ Пользователь с ID {user_id} не найден в базе.")
        else:
            issue_coupon(bot, user_id, user_id)
            bot.send_message(admin_id, f"✅ Купон успешно выдан пользователю {user_data['first_name']} (ID: {user_id}).")
        if admin_id in admin_states:
            del admin_states[admin_id]
        
    def process_password_word_step(message: types.Message):
        if not is_admin(message.from_user.id): return
        new_word = message.text
        msg = bot.send_message(message.chat.id, texts.BOSS_ASK_PASSWORD_BONUS)
        bot.register_next_step_handler(msg, process_password_bonus_step, new_word)

    def process_password_bonus_step(message: types.Message, word):
        if not is_admin(message.from_user.id): return
        new_bonus = message.text
        settings_manager.update_setting("promotions.password_of_the_day.password", word)
        settings_manager.update_setting("promotions.password_of_the_day.bonus_text", new_bonus)
        bot.send_message(message.chat.id, texts.BOSS_PASSWORD_SUCCESS)
        
    def process_audio_upload_step(message: types.Message):
        if not is_admin(message.from_user.id): return
        if message.audio:
            file_id = message.audio.file_id
            settings_manager.update_setting("greeting_audio_id", file_id)
            bot.reply_to(message, "✅ Аудио-приветствие сохранено!")
            logging.info(f"Админ {message.from_user.id} загрузил новое аудио. File ID: {file_id}")
        else:
            bot.reply_to(message, "Это не аудиофайл. Попробуй еще раз.")

    # Регистрируем обработчики из новых файлов
    handle_report_callbacks(bot, admin_states, settings_manager, keyboards, texts)
    handle_staff_callbacks(bot, keyboards)
    handle_user_callbacks(bot, admin_states, texts)
    handle_promotions_callbacks(bot, settings_manager, keyboards)
    handle_content_callbacks(bot, texts)

    # --- Основной обработчик кнопок админки ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_') or call.data.startswith('boss_'))
    def handle_admin_callbacks(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, texts.ADMIN_ACCESS_DENIED, show_alert=True)
            return
        
        action = call.data
        bot.answer_callback_query(call.id)
        
        try:
            # НАВИГАЦИЯ
            if action == 'admin_main_menu':
                bot.edit_message_text("👑 **Главное меню админ-панели**\n\nВыберите нужный раздел:", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_main_menu())
            elif action == 'admin_menu_promotions':
                settings = settings_manager.get_all_settings()
                bot.edit_message_text("⚙️ **Управление акциями**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_promotions_menu(settings))
            elif action == 'admin_menu_reports':
                bot.edit_message_text("📊 **Отчеты и аналитика**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_reports_menu())
            elif action == 'admin_menu_content':
                bot.edit_message_text("📝 **Управление контентом**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_content_menu())
            elif action == 'admin_menu_users':
                bot.edit_message_text("👤 **Управление пользователями**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_users_menu())
            elif action == 'admin_menu_data':
                bot.edit_message_text("💾 **Управление данными**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_data_menu())
            elif action == 'admin_menu_staff':
                bot.edit_message_text("👥 **Управление персоналом**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_staff_menu())
            
            # ДЕЙСТВИЯ
            elif action == 'admin_find_user':
                msg = bot.send_message(call.message.chat.id, "Введите ID или @username пользователя для поиска:")
                admin_states[call.from_user.id] = 'awaiting_user_identifier'
                bot.register_next_step_handler(msg, process_find_user_step)
            elif action == 'admin_issue_coupon_manual':
                msg = bot.send_message(call.message.chat.id, "Введите ID пользователя, которому нужно выдать купон:")
                admin_states[call.from_user.id] = 'awaiting_coupon_user_id'
                bot.register_next_step_handler(msg, process_issue_coupon_step)
            elif action == 'admin_export_sheets':
                bot.send_message(call.message.chat.id, "⏳ Начинаю выгрузку в Google Sheets... Это может занять до минуты.")
                success, message = do_export()
                bot.send_message(call.message.chat.id, message)
            
            # ОТЧЕТЫ
            elif action == 'admin_report_manual_daily':
                tz_moscow = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(tz_moscow)
                start_time = end_time - datetime.timedelta(days=1)
                send_report(bot, call.message.chat.id, start_time, end_time)
            elif action == 'admin_churn_analysis':
                total_left, distribution = database.get_full_churn_analysis()
                if total_left == 0:
                    bot.send_message(call.message.chat.id, "Пока никто из получивших подарок не отписался. Отличная работа!")
                else:
                    response = f"💔 **Анализ оттока подписчиков (за все время)**\n\nВсего отписалось после подарка: **{total_left}** чел.\n\n**Как быстро они отписываются:**\n"
                    for period, count in distribution.items():
                        percentage = round((count / total_left) * 100, 1) if total_left > 0 else 0
                        response += f"• {period}: **{count}** чел. ({percentage}%)\n"
                    bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
            elif action == 'admin_report_leaderboard':
                top_list = database.get_top_referrers_for_month(5)
                if not top_list:
                    bot.send_message(call.message.chat.id, "В этом месяце пока никто не привел друзей, которые бы получили настойку.")
                else:
                    month_name = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%B %Y')
                    response = f"🏆 **Ударники труда за {month_name}**:\n(учитываются только друзья, погасившие настойку в этом месяце)\n\n"
                    medals = ["🥇", "🥈", "🥉", "4.", "5."]
                    for i, (name, count) in enumerate(top_list):
                        response += f"{medals[i]} Товарищ **{name}** — {count} чел.\n"
                    bot.send_message(call.message.chat.id, response, parse_mode="Markdown")

            # ОТЧЕТЫ (реализация)
            elif action == 'admin_report_source_funnel':
                tz_moscow = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(tz_moscow)
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
                tz_moscow = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(tz_moscow)
                start_time = end_time - datetime.timedelta(days=30)
                # Получаем отток по источникам
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
                tz_moscow = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(tz_moscow)
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

            # УПРАВЛЕНИЕ КОНТЕНТОМ И АКЦИЯМИ
            elif action.startswith('boss_toggle_'):
                feature_path = action.replace('boss_toggle_', '')
                current_value = settings_manager.get_setting(feature_path)
                settings_manager.update_setting(feature_path, not current_value)
                new_settings = settings_manager.get_all_settings()
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_promotions_menu(new_settings))
            elif action == 'boss_upload_audio':
                msg = bot.send_message(call.message.chat.id, "Отправь мне аудиофайл...")
                bot.register_next_step_handler(msg, process_audio_upload_step)
            elif action == 'boss_set_password':
                msg = bot.send_message(call.message.chat.id, texts.BOSS_ASK_PASSWORD_WORD)
                bot.register_next_step_handler(msg, process_password_word_step)
                
        except ApiTelegramException as e:
            logging.warning(f"Не удалось обработать колбэк в админ-панели: {e}")

    @bot.message_handler(commands=['restart'])
    def handle_restart_command(message: types.Message):
        if not is_admin(message.from_user.id):
            return
        user_id = message.from_user.id
        success, response_message = database.delete_user(user_id)
        if success:
            bot.reply_to(message, f"✅ Успех: {response_message}\nМожете начинать тестирование заново, отправив команду /start.")
        else:
            bot.reply_to(message, f"❌ Ошибка при сбросе профиля: {response_message}")
