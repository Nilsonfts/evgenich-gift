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

# --- Утилита для сокращения имени ---
def shorten_name(full_name: str) -> str:
    """Превращает 'Иван Смирнов' в 'Иван С.'."""
    parts = full_name.split()
    if len(parts) > 1:
        return f"{parts[0]} {parts[1][0]}."
    return full_name

# --- Функции генерации отчетов ---
def generate_daily_report_text(start_time, end_time, general_stats, staff_stats):
    """Формирует текст полного ежедневного отчета."""
    issued, redeemed, _, sources, total_redeem_time = general_stats
    _, left_count = database.get_daily_churn_data(start_time, end_time)

    # Блок общей статистики
    conversion_rate = round((redeemed / issued) * 100, 1) if issued > 0 else 0
    avg_redeem_time_str = "н/д"
    if redeemed > 0:
        avg_seconds = total_redeem_time / redeemed
        hours, remainder = divmod(int(avg_seconds), 3600)
        minutes, _ = divmod(remainder, 60)
        avg_redeem_time_str = f"{hours} ч {minutes} мин"
    
    retention_rate_str = "н/д"
    if redeemed > 0:
        retention_rate = round(((redeemed - left_count) / redeemed) * 100, 1)
        retention_rate_str = f"{retention_rate}%"

    report_date = end_time.strftime('%d.%m.%Y')
    header = f"📊 **ОтчетПодпискаТГ ({report_date})** 📊\n\n"
    period_str = f"**Период:** с {start_time.strftime('%H:%M %d.%m')} по {end_time.strftime('%H:%M %d.%m')}\n\n"
    
    stats_block = (f"✅ **Выдано купонов:** {issued}\n"
                   f"🥃 **Погашено настоек:** {redeemed}\n"
                   f"📈 **Конверсия в погашение:** {conversion_rate}%\n"
                   f"⏱️ **Среднее время до погашения:** {avg_redeem_time_str}\n"
                   f"💔 **Отписалось за сутки:** {left_count} чел.\n"
                   f"🎯 **Удержание за сутки:** {retention_rate_str}\n")
    
    # Блок источников
    sources_block = ""
    if sources:
        sources_block += "\n---\n\n**Источники подписчиков (общие):**\n"
        # Убираем из общих источников те, что относятся к персоналу
        filtered_sources = {k: v for k, v in sources.items() if not k.startswith("Сотрудник:")}
        sorted_sources = sorted(filtered_sources.items(), key=lambda item: item[1], reverse=True)
        for source, count in sorted_sources:
            sources_block += f"• {source}: {count}\n"
            
    # Блок персонала
    staff_block = ""
    if staff_stats:
        staff_block += "\n---\n\n**🏆 Эффективность персонала (за сутки) 🏆**\n"
        # Сортируем должности для стабильного порядка
        for position in sorted(staff_stats.keys()):
            position_rus = f"{position}ы"
            if position == "Менеджер": position_rus = "Менеджеры"
            
            emoji_map = {"Официант": "🤵", "Бармен": "🍸", "Менеджер": "🎩"}
            emoji = emoji_map.get(position, "👥")

            staff_block += f"\n**{emoji} {position_rus}:**\n"
            sorted_staff = sorted(staff_stats[position], key=lambda x: x['brought'], reverse=True)
            medals = ["🥇", "🥈", "🥉"]
            for i, staff in enumerate(sorted_staff):
                medal = medals[i] if i < len(medals) else "•"
                staff_block += f"{medal} **{staff['name']}** | Гостей: **{staff['brought']}** (Отток: {staff['churn']})\n"
    else:
        staff_block = "\n\n---\n\n**🏆 Эффективность персонала (за сутки) 🏆**\n\n_Сегодня никто из персонала не приводил гостей через бота._"

    return header + period_str + stats_block + sources_block + staff_block

def send_report(bot, chat_id, start_time, end_time):
    """Запрашивает все данные и отправляет единый отчет."""
    try:
        general_stats = database.get_report_data_for_period(start_time, end_time)
        staff_stats = database.get_staff_performance_for_period(start_time, end_time)

        if general_stats[0] == 0: # Проверяем issued
            bot.send_message(chat_id, f"За период с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')} нет данных для отчета.")
            return

        report_text = generate_daily_report_text(start_time, end_time, general_stats, staff_stats)
        bot.send_message(chat_id, report_text, parse_mode="Markdown")
        
        # Логика для "Ударника дня"
        all_staff_results = []
        for position in staff_stats:
            all_staff_results.extend(staff_stats[position])
        
        if all_staff_results:
            winner = max(all_staff_results, key=lambda x: x['brought'])
            if winner['brought'] > 0:
                winner_name = winner['name']
                # Тут будет вызов нейросети в будущем. Пока - шаблон.
                winner_text = (f"💥 **ГЕРОЙ ДНЯ!** 💥\n\n"
                               f"Сегодня всех обошел(ла) **{winner_name}**, приведя **{winner['brought']}** новых гостей! "
                               f"Отличная работа, так держать! 👏🥳")
                bot.send_message(chat_id, winner_text)

    except Exception as e:
        logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")
        bot.send_message(chat_id, "Ошибка при формировании отчета.")


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
            response = (f"👤 **Профиль пользователя:**\n\n"
                        f"**ID:** `{user_data['user_id']}`\n"
                        f"**Имя:** {user_data['first_name']}\n"
                        f"**Юзернейм:** @{user_data['username'] or 'Нет'}\n"
                        f"**Статус:** {status_ru}\n"
                        f"**Источник:** {user_data['source'] or 'Неизвестен'}\n"
                        f"**Пригласил:** {user_data['referrer_id'] or 'Никто'}\n"
                        f"**Привел сотрудник:** {user_data['brought_by_staff_id'] or 'Нет'}\n"
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
                bot.edit_message_text("👑 **Главное меню админ-панели**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_main_menu())
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
            elif action == 'admin_list_staff':
                all_staff = database.get_all_staff()
                if not all_staff:
                    bot.send_message(call.message.chat.id, "В системе пока нет ни одного сотрудника.")
                    return
                
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, "📋 **Список сотрудников:**\n(Нажмите на кнопку под сообщением, чтобы изменить статус)")
                for staff in all_staff:
                    status_icon = "✅ Активен" if staff['status'] == 'active' else "❌ Неактивен"
                    response = f"{staff['full_name']} ({staff['position']})\nСтатус: {status_icon} | ID: `{staff['telegram_id']}`"
                    bot.send_message(call.message.chat.id, response, parse_mode="Markdown", reply_markup=keyboards.get_staff_management_keyboard(staff['staff_id'], staff['status']))

            elif action.startswith('admin_toggle_staff_'):
                parts = action.split('_')
                staff_id, new_status = int(parts[3]), parts[4]
                database.update_staff_status(staff_id, new_status)
                
                # Обновляем сообщение с кнопкой
                all_staff = database.get_all_staff()
                for s in all_staff:
                    if s['staff_id'] == staff_id:
                        status_icon = "✅ Активен" if new_status == 'active' else "❌ Неактивен"
                        new_text = f"{s['full_name']} ({s['position']})\nСтатус: {status_icon} | ID: `{s['telegram_id']}`"
                        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown",
                                              reply_markup=keyboards.get_staff_management_keyboard(s['staff_id'], new_status))
                        break
            
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
                # ... (этот и другие отчеты мы добавим на следующем шаге)
                bot.send_message(call.message.chat.id, "Отчет 'Анализ оттока' в разработке.")


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
