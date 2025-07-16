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
import marketing_templates
from export_to_sheets import do_export
from handlers.user_commands import issue_coupon
from handlers.newsletter_manager import register_newsletter_handlers
from handlers.newsletter_buttons import register_newsletter_buttons_handlers

# --- Утилита для сокращения имени ---
def shorten_name(full_name: str) -> str:
    """Превращает 'Иван Смирнов' в 'Иван С.'."""
    parts = full_name.split()
    if len(parts) > 1:
        return f"{parts[0]} {parts[1][0]}."
    return full_name

# --- Функции генерации отчетов ---

# --- Функции генерации отчетов ---
def generate_daily_report_text(start_time, end_time, general_stats, staff_stats, iiko_count=None, is_current_shift=False):
    """Формирует текст полного ежедневного отчета."""
    issued, redeemed, _, sources, total_redeem_time = general_stats
    _, left_count = database.get_daily_churn_data(start_time, end_time)

    # Блок общей статистики
    conversion_rate = round((redeemed / issued) * 100, 1) if issued > 0 else 0
    avg_redeem_time_str = "н/д"
    if redeemed > 0 and total_redeem_time > 0:
        avg_seconds = total_redeem_time / redeemed
        hours, remainder = divmod(int(avg_seconds), 3600)
        minutes, _ = divmod(remainder, 60)
        avg_redeem_time_str = f"{hours} ч {minutes} мин"
    
    retention_rate_str = "н/д"
    if redeemed > 0:
        retention_rate = round(((redeemed - left_count) / redeemed) * 100, 1)
        retention_rate_str = f"{retention_rate}%"

    report_date = end_time.strftime('%d.%m.%Y')
    if is_current_shift:
        header = f"� **Текущая смена ({report_date})** 🔥\n\n"
        period_str = f"**Смена в процессе:** с {start_time.strftime('%H:%M %d.%m')} по сейчас ({end_time.strftime('%H:%M %d.%m')})\n\n"
    else:
        header = f"�📊 **Отчет за смену ({report_date})** 📊\n\n"
        period_str = f"**Завершенная смена:** с {start_time.strftime('%H:%M %d.%m')} по {end_time.strftime('%H:%M %d.%m')}\n\n"
    
    # Добавляем информацию о настойках iiko
    iiko_info = ""
    if iiko_count is not None:
        iiko_info = f"🍷 **Пробито настоек в iiko:** {iiko_count}\n"
    else:
        iiko_info = f"🍷 **Пробито настоек в iiko:** данные не получены\n"
    
    stats_block = (f"✅ **Выдано купонов:** {issued}\n"
                   f"🥃 **Погашено настоек:** {redeemed}\n" +
                   iiko_info +
                   f"📈 **Конверсия в погашение:** {conversion_rate}%\n"
                   f"⏱️ **Среднее время до погашения:** {avg_redeem_time_str}\n"
                   f"💔 **Отписалось за сутки:** {left_count} чел.\n"
                   f"🎯 **Удержание за сутки:** {retention_rate_str}\n")
    
    # Блок источников
    sources_block = ""
    if sources:
        sources_block += "\n---\n\n**Источники подписчиков (общие):**\n"
        filtered_sources = {k: v for k, v in sources.items() if not k.startswith("Сотрудник:")}
        sorted_sources = sorted(filtered_sources.items(), key=lambda item: item[1], reverse=True)
        for source, count in sorted_sources:
            sources_block += f"• {source}: {count}\n"
            
    # Блок персонала
    staff_block = ""
    if staff_stats:
        staff_block += "\n---\n\n**🏆 Эффективность персонала (за сутки) 🏆**\n"
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
                staff_name_short = shorten_name(staff['name'])
                staff_block += f"{medal} **{staff_name_short}** | Гостей: **{staff['brought']}** (Отток: {staff['churn']})\n"
    else:
        staff_block = "\n\n---\n\n**🏆 Эффективность персонала (за сутки) 🏆**\n\n_Сегодня никто из персонала не приводил гостей через бота._"

    return header + period_str + stats_block + sources_block + staff_block

def send_report(bot, chat_id, start_time, end_time, is_current_shift=False):
    """Запрашивает все данные и отправляет единый отчет."""
    try:
        general_stats = database.get_report_data_for_period(start_time, end_time)
        staff_stats = database.get_staff_performance_for_period(start_time, end_time)
        
        # Получаем данные iiko за дату окончания смены
        iiko_count = database.get_iiko_nastoika_count_for_date(end_time.date())

        if general_stats[0] == 0:
            period_desc = "текущей смены" if is_current_shift else "указанного периода"
            bot.send_message(chat_id, f"За период с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')} нет данных для отчета по {period_desc}.")
            return

        report_text = generate_daily_report_text(start_time, end_time, general_stats, staff_stats, iiko_count, is_current_shift)
        bot.send_message(chat_id, report_text, parse_mode="Markdown")
        
        # Логика для "Ударника дня"
        all_staff_results = []
        for position in staff_stats:
             for staff_member in staff_stats[position]:
                all_staff_results.append(staff_member)
        
        if all_staff_results:
            winner = max(all_staff_results, key=lambda x: x['brought'])
            if winner['brought'] > 0:
                winner_name = shorten_name(winner['name'])
                winner_text = (f"💥 **ГЕРОЙ ДНЯ!** 💥\n\n"
                               f"Сегодня всех обошел(ла) **{winner_name}**, приведя **{winner['brought']}** новых гостей! "
                               f"Отличная работа, так держать! 👏🥳")
                # Тут будет логика тега и AI
                bot.send_message(chat_id, winner_text)

    except Exception as e:
        logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")
        bot.send_message(chat_id, "Ошибка при формировании отчета.")


def register_admin_handlers(bot):
    """Регистрирует все команды и колбэки для админ-панели."""
    admin_states = {}

    def is_admin(user_id):
        return user_id in ADMIN_IDS

    def _show_newsletter_audience_stats(message):
        """Показывает статистику базы для рассылок."""
        try:
            conn = database.get_db_connection()
            cur = conn.cursor()
            
            # Общая статистика пользователей
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'registered'")
            registered_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'issued'")
            issued_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed'")
            redeemed_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed_and_left'")
            churned_count = cur.fetchone()[0]
            
            # Активная аудитория для рассылок
            active_for_newsletter = registered_count + issued_count + redeemed_count
            
            # Статистика по источникам
            cur.execute("SELECT source, COUNT(*) as count FROM users GROUP BY source ORDER BY count DESC LIMIT 5")
            source_stats = cur.fetchall()
            
            conn.close()
            
            stats_text = (
                f"📊 **Статистика базы подписчиков**\n\n"
                f"**👥 Общая статистика:**\n"
                f"• Всего пользователей: **{total_users}**\n"
                f"• Зарегистрированы: **{registered_count}**\n"
                f"• Получили купоны: **{issued_count}**\n"
                f"• Погасили купоны: **{redeemed_count}**\n"
                f"• Отписались: **{churned_count}**\n\n"
                f"📧 **Для рассылок:**\n"
                f"• Активная аудитория: **{active_for_newsletter}** чел.\n"
                f"• Исключены (отписались): **{churned_count}** чел.\n\n"
                f"📈 **Топ источников:**\n"
            )
            
            for source, count in source_stats:
                source_name = source or "Неизвестно"
                stats_text += f"• {source_name}: **{count}** чел.\n"
            
            bot.edit_message_text(
                stats_text,
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_content_management_menu(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка показа статистики аудитории: {e}")
            bot.send_message(message.chat.id, "Ошибка получения статистики")

    def _show_newsletters_list(message):
        """Показывает список рассылок."""
        try:
            conn = database.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, title, status, created_at, target_count, delivered_count
                FROM newsletters 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            newsletters = cur.fetchall()
            conn.close()
            
            if not newsletters:
                list_text = "📋 **Ваши рассылки**\n\nПока нет созданных рассылок."
            else:
                list_text = "📋 **Ваши рассылки:**\n\n"
                
                for newsletter in newsletters:
                    status_emoji = {
                        'draft': '📝',
                        'scheduled': '⏰',
                        'sent': '✅',
                        'sending': '📤'
                    }.get(newsletter[2], '❓')
                    
                    delivery_info = ""
                    if newsletter[4] and newsletter[5]:  # target_count и delivered_count
                        delivery_info = f" ({newsletter[5]}/{newsletter[4]})"
                    
                    list_text += f"{status_emoji} **{newsletter[1]}**{delivery_info}\n"
            
            bot.edit_message_text(
                list_text,
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_content_management_menu(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка показа списка рассылок: {e}")
            bot.send_message(message.chat.id, "Ошибка получения списка рассылок")

    def _show_analytics_overview(message):
        """Показывает общую аналитику рассылок."""
        try:
            conn = database.get_db_connection()
            cur = conn.cursor()
            
            # Общая статистика рассылок
            cur.execute("SELECT COUNT(*) FROM newsletters")
            total_newsletters = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM newsletters WHERE status = 'sent'")
            sent_newsletters = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(target_count) FROM newsletters WHERE status = 'sent'")
            total_sent = cur.fetchone()[0] or 0
            
            cur.execute("SELECT SUM(delivered_count) FROM newsletters WHERE status = 'sent'")
            total_delivered = cur.fetchone()[0] or 0
            
            # Статистика кликов
            cur.execute("SELECT COUNT(*) FROM newsletter_clicks")
            total_clicks = cur.fetchone()[0]
            
            # Топ кнопок по кликам
            cur.execute("""
                SELECT nb.text, COUNT(nc.id) as clicks
                FROM newsletter_buttons nb
                LEFT JOIN newsletter_clicks nc ON nb.id = nc.button_id
                GROUP BY nb.id, nb.text
                ORDER BY clicks DESC
                LIMIT 5
            """)
            top_buttons = cur.fetchall()
            
            conn.close()
            
            # Расчет CTR
            ctr = 0
            if total_delivered > 0:
                ctr = round((total_clicks / total_delivered) * 100, 1)
            
            analytics_text = (
                f"📈 **Общая аналитика рассылок**\n\n"
                f"**📊 Статистика:**\n"
                f"• Всего рассылок: **{total_newsletters}**\n"
                f"• Отправлено: **{sent_newsletters}**\n"
                f"• Сообщений доставлено: **{total_delivered}**\n"
                f"• Всего кликов: **{total_clicks}**\n"
                f"• CTR: **{ctr}%**\n\n"
            )
            
            if top_buttons:
                analytics_text += "🔥 **Топ кнопок по кликам:**\n"
                for button_text, clicks in top_buttons:
                    if clicks > 0:
                        analytics_text += f"• {button_text}: **{clicks}** кликов\n"
            
            bot.edit_message_text(
                analytics_text,
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_content_management_menu(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка показа аналитики: {e}")
            bot.send_message(message.chat.id, "Ошибка получения аналитики")

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
            elif action == 'admin_newsletter_main':
                bot.edit_message_text("📧 **Система рассылок**\n\nВыберите действие:", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_content_management_menu(), parse_mode="Markdown")
            
            # ОБРАБОТЧИКИ СИСТЕМЫ РАССЫЛОК
            elif action == 'admin_content_stats':
                _show_newsletter_audience_stats(call.message)
            elif action == 'admin_content_create':
                bot.edit_message_text("✉️ **Создание рассылки**\n\nВыберите тип рассылки:", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_newsletter_creation_menu(), parse_mode="Markdown")
            elif action == 'admin_content_list':
                _show_newsletters_list(call.message)
            elif action == 'admin_content_analytics':
                _show_analytics_overview(call.message)
            
            # ОБРАБОТЧИКИ СИСТЕМЫ РАССЫЛОК
            elif action == 'admin_content_stats':
                # Статистика базы для рассылок
                try:
                    conn = database.get_db_connection()
                    cur = conn.cursor()
                    
                    # Общая статистика пользователей
                    cur.execute("SELECT COUNT(*) FROM users")
                    total_users = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM users WHERE status = 'registered'")
                    registered = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM users WHERE status = 'issued'")
                    issued = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed'")
                    redeemed = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed_and_left'")
                    blocked = cur.fetchone()[0]
                    
                    # Активные для рассылок (исключаем заблокированных)
                    active_for_newsletter = total_users - blocked
                    
                    # Дополнительная статистика по источникам
                    cur.execute("SELECT source, COUNT(*) FROM users WHERE status != 'redeemed_and_left' GROUP BY source ORDER BY COUNT(*) DESC LIMIT 5")
                    top_sources = cur.fetchall()
                    
                    # Статистика по времени регистрации (последние 7 дней)
                    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                    cur.execute("SELECT COUNT(*) FROM users WHERE signup_date >= ? AND status != 'redeemed_and_left'", (week_ago,))
                    new_week = cur.fetchone()[0]
                    
                    conn.close()
                    
                    stats_text = (
                        f"📊 **Статистика базы для рассылок**\n\n"
                        f"👥 **Всего пользователей:** {total_users}\n"
                        f"📝 **Зарегистрированы:** {registered}\n"
                        f"🎁 **Получили купоны:** {issued}\n"
                        f"✅ **Погасили купоны:** {redeemed}\n"
                        f"🚫 **Заблокировали бота:** {blocked}\n\n"
                        f"📧 **Доступно для рассылки:** {active_for_newsletter}\n"
                        f"🆕 **Новых за неделю:** {new_week}\n\n"
                        f"🎯 **Топ источников:**\n"
                    )
                    
                    for source, count in top_sources:
                        source_name = source or "Неизвестно"
                        stats_text += f"• {source_name}: {count}\n"
                    
                    stats_text += f"\n💡 Рассылка будет отправлена **{active_for_newsletter}** подписчикам"
                    
                    bot.edit_message_text(
                        stats_text,
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=keyboards.get_content_management_menu(),
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"Ошибка получения статистики: {e}")
            
            elif action == 'admin_content_create':
                # Создание новой рассылки с выбором шаблонов
                bot.edit_message_text(
                    "✉️ **Создание рассылки**\n\n"
                    "Выберите способ создания:\n\n"
                    "🎯 **С шаблоном** — быстро и профессионально\n"
                    "✏️ **Свой текст** — полная свобода творчества",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.get_newsletter_creation_choice_menu(),
                    parse_mode="Markdown"
                )
            
            # Новые обработчики для шаблонной системы
            elif action == 'admin_newsletter_template_choice':
                bot.edit_message_text(
                    "🎯 **Выбор шаблона рассылки**\n\n"
                    "Выберите категорию шаблона:\n\n"
                    "🎉 **Акции и скидки** — промо-кампании\n"
                    "🍽 **Новое меню** — новинки и блюда дня\n"
                    "🎵 **Мероприятия** — концерты и события\n"
                    "📅 **Бронирование** — напоминания о столах\n"
                    "👋 **Приветствие** — welcome-сообщения",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.get_newsletter_template_categories(),
                    parse_mode="Markdown"
                )
            
            elif action == 'admin_newsletter_custom_choice':
                bot.edit_message_text(
                    "✏️ **Создание своей рассылки**\n\n"
                    "Выберите тип контента:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.get_newsletter_creation_menu(),
                    parse_mode="Markdown"
                )
            
            # Обработчики категорий шаблонов
            elif action.startswith('admin_template_'):
                template_category = action.replace('admin_template_', '')
                _show_template_preview(bot, call.message, template_category)
            
            elif action.startswith('admin_use_template_'):
                template_category = action.replace('admin_use_template_', '')
                _use_template(bot, call.message, template_category, call.from_user.id)
            
            elif action.startswith('admin_edit_template_'):
                template_category = action.replace('admin_edit_template_', '')
                _edit_template(bot, call.message, template_category, call.from_user.id)
            
            elif action == 'admin_content_list':
                # Список рассылок
                try:
                    newsletters = database.get_user_newsletters(call.from_user.id, 10)
                    
                    if not newsletters:
                        bot.edit_message_text(
                            "📋 **Мои рассылки**\n\nУ вас пока нет созданных рассылок.\nСоздайте свою первую рассылку!",
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=keyboards.get_content_management_menu(),
                            parse_mode="Markdown"
                        )
                    else:
                        list_text = "📋 **Мои рассылки:**\n\n"
                        for newsletter in newsletters[:5]:
                            status_emoji = {
                                'draft': '📝',
                                'scheduled': '⏰',
                                'sent': '✅',
                                'sending': '📤'
                            }.get(newsletter['status'], '❓')
                            
                            list_text += f"{status_emoji} **{newsletter['title']}**\n"
                            list_text += f"Статус: {newsletter['status']}\n"
                            if newsletter['created_at']:
                                list_text += f"Создана: {newsletter['created_at'][:16]}\n"
                            list_text += "\n"
                        
                        bot.edit_message_text(
                            list_text,
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=keyboards.get_content_management_menu(),
                            parse_mode="Markdown"
                        )
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"Ошибка получения списка рассылок: {e}")
            
            elif action == 'admin_content_analytics':
                # Общая аналитика рассылок
                try:
                    conn = database.get_db_connection()
                    cur = conn.cursor()
                    
                    # Общая статистика рассылок
                    cur.execute("SELECT COUNT(*) FROM newsletters")
                    total_newsletters = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM newsletters WHERE status = 'sent'")
                    sent_newsletters = cur.fetchone()[0]
                    
                    cur.execute("SELECT SUM(target_count) FROM newsletters WHERE status = 'sent'")
                    total_sent = cur.fetchone()[0] or 0
                    
                    cur.execute("SELECT SUM(delivered_count) FROM newsletters WHERE status = 'sent'")
                    total_delivered = cur.fetchone()[0] or 0
                    
                    cur.execute("SELECT COUNT(*) FROM newsletter_clicks")
                    total_clicks = cur.fetchone()[0]
                    
                    conn.close()
                    
                    analytics_text = (
                        f"📈 **Аналитика рассылок**\n\n"
                        f"📧 **Всего рассылок:** {total_newsletters}\n"
                        f"✅ **Отправлено:** {sent_newsletters}\n"
                        f"📤 **Сообщений отправлено:** {total_sent}\n"
                        f"📥 **Доставлено:** {total_delivered}\n"
                        f"👆 **Всего кликов:** {total_clicks}\n\n"
                    )
                    
                    if total_delivered > 0:
                        ctr = round((total_clicks / total_delivered) * 100, 1)
                        analytics_text += f"📊 **Общий CTR:** {ctr}%"
                    else:
                        analytics_text += "📊 **CTR:** Нет данных"
                    
                    bot.edit_message_text(
                        analytics_text,
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=keyboards.get_content_management_menu(),
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"Ошибка получения аналитики: {e}")
            elif action == 'admin_menu_users':
                bot.edit_message_text("👤 **Управление пользователями**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_users_menu())
            elif action == 'admin_menu_data':
                bot.edit_message_text("💾 **Управление данными**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_data_menu())
            elif action == 'admin_menu_staff':
                bot.edit_message_text("👥 **Управление персоналом**", call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_staff_menu())
            
            # УПРАВЛЕНИЕ ПЕРСОНАЛОМ
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
                if database.update_staff_status(staff_id, new_status):
                    all_staff = database.get_all_staff() # Получаем обновленный список
                    for s in all_staff:
                        if s['staff_id'] == staff_id:
                            status_icon = "✅ Активен" if new_status == 'active' else "❌ Неактивен"
                            new_text = f"{s['full_name']} ({s['position']})\nСтатус: {status_icon} | ID: `{s['telegram_id']}`"
                            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown",
                                                  reply_markup=keyboards.get_staff_management_keyboard(s['staff_id'], new_status))
                            break
                else:
                    bot.edit_message_text("Не удалось обновить статус.", call.message.chat.id, call.message.message_id, reply_markup=None)

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
            elif action == 'admin_report_current_shift':
                # Отчет по текущей смене в реальном времени
                tz_moscow = pytz.timezone('Europe/Moscow')
                current_time = datetime.datetime.now(tz_moscow)
                
                # Определяем начало ТЕКУЩЕЙ смены
                if current_time.hour >= 12:
                    # Текущая смена началась сегодня в 12:00
                    start_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
                    end_time = current_time  # До сейчас
                else:
                    # Текущая смена началась вчера в 12:00
                    start_time = (current_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
                    end_time = current_time  # До сейчас
                
                send_report(bot, call.message.chat.id, start_time, end_time, is_current_shift=True)
                
            elif action == 'admin_report_manual_daily':
                # Отчет за ЗАВЕРШЕННУЮ смену (вчерашнюю)
                tz_moscow = pytz.timezone('Europe/Moscow')
                current_time = datetime.datetime.now(tz_moscow)
                
                # Всегда берем завершенную смену (вчерашнюю)
                if current_time.hour >= 12:
                    # Сейчас дневное время - берем смену: вчера 12:00 - сегодня 06:00
                    end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                    start_time = (current_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
                else:
                    # Сейчас утро - берем смену: позавчера 12:00 - вчера 06:00
                    end_time = (current_time - datetime.timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
                    start_time = (current_time - datetime.timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)
                
                send_report(bot, call.message.chat.id, start_time, end_time, is_current_shift=False)
            elif action == 'admin_report_staff_realtime':
                # Статистика сотрудников в режиме реального времени за текущую смену
                tz_moscow = pytz.timezone('Europe/Moscow')
                current_time = datetime.datetime.now(tz_moscow)
                
                # Определяем начало текущей смены
                if current_time.hour >= 12:
                    # Текущая смена началась сегодня в 12:00
                    start_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
                else:
                    # Текущая смена началась вчера в 12:00
                    start_time = (current_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
                
                staff_stats = database.get_staff_performance_for_period(start_time, current_time)
                
                if not staff_stats:
                    bot.send_message(call.message.chat.id, 
                        f"👷 **Статистика сотрудников в реальном времени**\n\n"
                        f"📅 С {start_time.strftime('%d.%m %H:%M')} по {current_time.strftime('%d.%m %H:%M')}\n\n"
                        f"За текущую смену никто из персонала не привел гостей через бота.")
                else:
                    response = (f"👷 **Статистика сотрудников в реальном времени**\n\n"
                               f"📅 С {start_time.strftime('%d.%m %H:%M')} по {current_time.strftime('%d.%m %H:%M')}\n\n")
                    
                    total_brought = 0
                    for position in staff_stats:
                        for staff_member in staff_stats[position]:
                            total_brought += staff_member['brought']
                    
                    response += f"🎯 **Всего приведено за смену:** {total_brought} гостей\n\n"
                    
                    for position in sorted(staff_stats.keys()):
                        position_rus = f"{position}ы"
                        if position == "Менеджер": position_rus = "Менеджеры"
                        
                        emoji_map = {"Официант": "🤵", "Бармен": "🍸", "Менеджер": "🎩"}
                        emoji = emoji_map.get(position, "👥")
                        
                        response += f"**{emoji} {position_rus}:**\n"
                        sorted_staff = sorted(staff_stats[position], key=lambda x: x['brought'], reverse=True)
                        
                        for staff_member in sorted_staff:
                            staff_name_short = shorten_name(staff_member['name'])
                            response += f"• **{staff_name_short}**: {staff_member['brought']} гостей"
                            if staff_member['churn'] > 0:
                                response += f" (отток: {staff_member['churn']})"
                            response += "\n"
                        response += "\n"
                    
                    bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
            elif action == 'admin_staff_qr_diagnostics':
                # Диагностика QR-кодов сотрудников
                try:
                    conn = database.get_db_connection()
                    cur = conn.cursor()
                    
                    # Получаем всех активных сотрудников
                    cur.execute("SELECT staff_id, full_name, short_name, unique_code, position FROM staff WHERE status = 'active'")
                    active_staff = cur.fetchall()
                    
                    # Получаем статистику переходов по QR-кодам за последние 7 дней
                    tz_moscow = pytz.timezone('Europe/Moscow')
                    current_time = datetime.datetime.now(tz_moscow)
                    week_ago = current_time - datetime.timedelta(days=7)
                    
                    cur.execute("""
                        SELECT source, COUNT(*) as count 
                        FROM users 
                        WHERE signup_date >= ? AND source LIKE 'Сотрудник:%'
                        GROUP BY source
                        ORDER BY count DESC
                    """, (week_ago,))
                    qr_stats = cur.fetchall()
                    
                    # Получаем переходы с некорректными кодами
                    cur.execute("""
                        SELECT source, COUNT(*) as count 
                        FROM users 
                        WHERE signup_date >= ? AND source LIKE 'Неизвестный_сотрудник_%'
                        GROUP BY source
                    """, (week_ago,))
                    invalid_codes = cur.fetchall()
                    
                    conn.close()
                    
                    response = "🔍 **Диагностика QR-кодов сотрудников**\n\n"
                    response += f"📅 Статистика за последние 7 дней ({week_ago.strftime('%d.%m')} - {current_time.strftime('%d.%m')})\n\n"
                    
                    # Показываем активных сотрудников
                    response += f"👥 **Активные сотрудники:** {len(active_staff)}\n"
                    for staff in active_staff:
                        qr_url = f"https://t.me/EvgenichTapBarBot?start=w_{staff['unique_code']}"
                        response += f"• {staff['short_name']} ({staff['position']}) - код: `{staff['unique_code']}`\n"
                    
                    response += "\n📊 **Переходы по QR-кодам:**\n"
                    if qr_stats:
                        total_qr_visitors = sum(row['count'] for row in qr_stats)
                        response += f"✅ Успешных переходов: **{total_qr_visitors}**\n"
                        for row in qr_stats:
                            staff_name = row['source'].replace('Сотрудник: ', '')
                            response += f"  • {staff_name}: {row['count']}\n"
                    else:
                        response += "✅ Успешных переходов: **0**\n"
                    
                    if invalid_codes:
                        response += f"\n❌ **Переходы с некорректными кодами:** {sum(row['count'] for row in invalid_codes)}\n"
                        for row in invalid_codes:
                            invalid_code = row['source'].replace('Неизвестный_сотрудник_', '')
                            response += f"  • Код `{invalid_code}`: {row['count']} попыток\n"
                        response += "\n💡 *Проверьте, что QR-коды генерируются с правильными кодами!*"
                    else:
                        response += "\n✅ **Некорректных кодов не обнаружено**"
                    
                    response += f"\n\n🔗 **Формат QR-ссылки:**\n`https://t.me/EvgenichTapBarBot?start=w_КОД`"
                    
                    bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Ошибка диагностики QR-кодов: {e}")
                    bot.send_message(call.message.chat.id, "❌ Ошибка при получении диагностики QR-кодов.")
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
            elif action == 'admin_report_churn_by_source':
                tz_moscow = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(tz_moscow)
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

    # Регистрируем обработчики отчетов - теперь встроены в основной обработчик выше
    logging.info("Обработчики админ-панели зарегистрированы")

def init_admin_handlers(bot, scheduler=None):
    """Инициализирует все обработчики админ-панели."""
    # Основные обработчики админ-панели уже зарегистрированы через декораторы
    
    # Регистрируем обработчики системы рассылок
    if scheduler:
        register_newsletter_handlers(bot, scheduler)
    else:
        logging.warning("Scheduler не передан, функции планирования рассылок недоступны")
    
    # Регистрируем обработчики кнопок рассылок
    register_newsletter_buttons_handlers(bot)
    
    logging.info("Все обработчики админ-панели инициализированы")

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ШАБЛОНАМИ ===

def _show_template_preview(bot, message, category):
    """Показывает предпросмотр шаблона."""
    try:
        template_data = marketing_templates.get_template_preview(category)
        
        preview_text = (
            f"🎯 **Предпросмотр шаблона: {template_data['category_name']}**\n\n"
            f"📝 **Заголовок:**\n{template_data['title']}\n\n"
            f"📄 **Текст:**\n{template_data['content']}\n\n"
            f"🔗 **Кнопки:**\n"
        )
        
        for button in template_data['buttons']:
            preview_text += f"• {button['text']}\n"
        
        preview_text += (
            f"\n💡 **Рекомендации:**\n"
            f"⏰ Лучшее время: {template_data['best_time']}\n"
            f"📊 UTM-кампания: {template_data['utm_campaign']}\n\n"
            f"Что делать дальше?"
        )
        
        bot.edit_message_text(
            preview_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_template_preview_keyboard(category),
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка показа шаблона: {e}")

def _use_template(bot, message, category, user_id):
    """Использует шаблон для создания рассылки."""
    try:
        template_data = marketing_templates.get_template_data(category)
        
        # Создаем черновик рассылки с данными шаблона
        newsletter_id = database.create_newsletter(
            user_id=user_id,
            title=template_data['title'],
            content=template_data['content'],
            media_type='text',
            buttons=template_data['buttons'],
            utm_campaign=template_data['utm_campaign']
        )
        
        success_text = (
            f"✅ **Шаблон применен!**\n\n"
            f"📝 Рассылка создана на основе шаблона **{template_data['category_name']}**\n\n"
            f"🎯 **Следующие шаги:**\n"
            f"• Проверьте содержание\n"
            f"• При необходимости отредактируйте\n"
            f"• Отправьте рассылку\n\n"
            f"💡 **Совет:** {template_data['marketing_tip']}"
        )
        
        bot.edit_message_text(
            success_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_content_management_menu(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка применения шаблона: {e}")

def _edit_template(bot, message, category, user_id):
    """Позволяет редактировать шаблон перед использованием."""
    try:
        template_data = marketing_templates.get_template_data(category)
        
        # Создаем черновик с возможностью редактирования
        newsletter_id = database.create_newsletter(
            user_id=user_id,
            title=template_data['title'],
            content=template_data['content'],
            media_type='text',
            buttons=template_data['buttons'],
            utm_campaign=template_data['utm_campaign']
        )
        
        edit_text = (
            f"✏️ **Редактирование шаблона**\n\n"
            f"📝 Создан черновик на основе шаблона **{template_data['category_name']}**\n\n"
            f"🎯 **Что можно изменить:**\n"
            f"• Заголовок рассылки\n"
            f"• Основной текст\n"
            f"• Кнопки и ссылки\n"
            f"• Время отправки\n\n"
            f"💡 **Рекомендация:** {template_data['marketing_tip']}"
        )
        
        bot.edit_message_text(
            edit_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_content_management_menu(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка редактирования шаблона: {e}")
