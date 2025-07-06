# /handlers/admin_panel.py

import logging
import datetime
from telebot import types
import pytz

# Импортируем всё необходимое
from config import ADMIN_IDS
from g_sheets import (
    delete_user, get_report_data_for_period, get_stats_by_source, 
    get_weekly_cohort_data, get_top_referrers
)
import texts
import keyboards

# --- Вспомогательные функции ---

def generate_report_text(start_time, end_time, issued, redeemed, redeemed_users, sources, total_redeem_time_seconds):
    """Формирует текстовое представление отчета."""
    conversion_rate = round((redeemed / issued) * 100, 1) if issued > 0 else 0
    avg_redeem_time_str = "н/д"
    
    if redeemed > 0:
        avg_seconds = total_redeem_time_seconds / redeemed
        hours, remainder = divmod(int(avg_seconds), 3600)
        minutes, _ = divmod(remainder, 60)
        avg_redeem_time_str = f"{hours} ч {minutes} мин"
        
    report_date = end_time.strftime('%d.%m.%Y')
    header = f"**#Настойка_за_Подписку (Аналитика за {report_date})**\n\n"
    period_str = f"**Период:** с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')}\n\n"
    stats = (f"✅ **Выдано купонов:** {issued}\n"
             f"🥃 **Погашено настоек:** {redeemed}\n"
             f"📈 **Конверсия:** {conversion_rate}%\n"
             f"⏱️ **Среднее время до погашения:** {avg_redeem_time_str}\n")
             
    sources_str = ""
    if sources:
        sources_str += "\n**Источники подписчиков:**\n"
        sorted_sources = sorted(sources.items(), key=lambda item: item[1], reverse=True)
        for source, count in sorted_sources:
            sources_str += f"• {source}: {count}\n"
            
    users_str = ""
    if redeemed_users:
        users_str += "\n**Настойку получили:**\n"
        for user in redeemed_users[:10]:
            users_str += f"• {user}\n"
        if len(redeemed_users) > 10:
            users_str += f"...и еще {len(redeemed_users) - 10}."
            
    return header + period_str + stats + sources_str + users_str

def send_report(bot, chat_id, start_time, end_time):
    """Запрашивает данные и отправляет отчет в указанный чат."""
    try:
        issued, redeemed, redeemed_users, sources, total_redeem_time = get_report_data_for_period(start_time, end_time)
        if issued == 0:
            bot.send_message(chat_id, f"За период с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')} нет данных для отчета.")
            return
        report_text = generate_report_text(start_time, end_time, issued, redeemed, redeemed_users, sources, total_redeem_time)
        bot.send_message(chat_id, report_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")
        bot.send_message(chat_id, "Ошибка при формировании отчета.")

# --- Регистрация обработчиков ---

def register_admin_handlers(bot):
    """Регистрирует все команды и колбэки для админ-панели."""

    def is_admin(user_id):
        return user_id in ADMIN_IDS

    @bot.message_handler(commands=['admin'])
    def handle_admin_command(message: types.Message):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, texts.ADMIN_ACCESS_DENIED)
            return
        bot.send_message(
            message.chat.id, 
            texts.ADMIN_MAIN_MENU, 
            reply_markup=keyboards.get_admin_main_keyboard(), 
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['restart'])
    def handle_restart_command(message: types.Message):
        if not is_admin(message.from_user.id):
            return
        user_id = message.from_user.id
        success, response_message = delete_user(user_id)
        if success:
            bot.reply_to(message, f"✅ Успех: {response_message}\nМожете начинать тестирование заново, отправив команду /start.")
        else:
            bot.reply_to(message, f"❌ Ошибка при сбросе профиля: {response_message}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_callbacks(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, texts.ADMIN_ACCESS_DENIED, show_alert=True)
            return
        
        bot.answer_callback_query(call.id)
        action = call.data
        
        # Навигация по меню
        if action == 'admin_menu_main':
            try:
                bot.edit_message_text(
                    texts.ADMIN_MAIN_MENU, call.message.chat.id, call.message.message_id, 
                    reply_markup=keyboards.get_admin_main_keyboard(), parse_mode="Markdown"
                )
            except: pass
        elif action == 'admin_menu_reports':
            bot.edit_message_text(
                texts.ADMIN_REPORTS_MENU, call.message.chat.id, call.message.message_id,
                reply_markup=keyboards.get_admin_reports_keyboard(), parse_mode="Markdown"
            )
        elif action == 'admin_menu_analytics':
            bot.edit_message_text(
                texts.ADMIN_ANALYTICS_MENU, call.message.chat.id, call.message.message_id,
                reply_markup=keyboards.get_admin_analytics_keyboard(), parse_mode="Markdown"
            )

        # Действия
        elif action == 'admin_action_leaderboard':
            top_list = get_top_referrers(5)
            if not top_list:
                bot.send_message(call.message.chat.id, "Пока никто не привел друзей, которые бы получили настойку.")
                return
            response = "**🏆 Доска Почета ударников труда:**\n(учитываются только друзья, которые погасили настойку)\n\n"
            medals = ["🥇", "🥈", "🥉", "4.", "5."]
            for i, (name, count) in enumerate(top_list):
                response += f"{medals[i]} Товарищ **{name}** — {count} чел.\n"
            bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
            
        elif action == 'admin_action_sources':
            stats = get_stats_by_source()
            if not stats:
                bot.send_message(call.message.chat.id, "Нет данных по источникам.")
                return
            response = "**📈 Анализ по источникам (за все время):**\n\n"
            sorted_stats = sorted(stats.items(), key=lambda item: item[1]['issued'], reverse=True)
            for source, data in sorted_stats:
                conversion = round((data['redeemed'] / data['issued']) * 100, 1) if data['issued'] > 0 else 0
                response += f"**{source}:**\n  Подписалось: {data['issued']}\n  Погашено: {data['redeemed']} (Конверсия: {conversion}%)\n\n"
            bot.send_message(call.message.chat.id, response, parse_mode="Markdown")

        elif action == 'admin_action_cohorts':
            cohorts = get_weekly_cohort_data()
            if not cohorts:
                bot.send_message(call.message.chat.id, "Недостаточно данных для анализа когорт.")
                return
            response = "**🗓️ Анализ по недельным когортам:**\n(сравниваем, как хорошо гости разных недель доходят до бара)\n\n"
            for cohort in cohorts:
                if cohort['issued'] == 0: continue
                conversion = round((cohort['redeemed'] / cohort['issued']) * 100, 1)
                response += f"**Неделя ({cohort['week']}):**\n  Новых: {cohort['issued']}, Погашено: {cohort['redeemed']} (Конверсия: {conversion}%)\n\n"
            bot.send_message(call.message.chat.id, response, parse_mode="Markdown")

        # Отчеты по периодам
        elif call.data.startswith('admin_report'):
            period = call.data.split('_')[-1]
            tz_moscow = pytz.timezone('Europe/Moscow')
            now_moscow = datetime.datetime.now(tz_moscow)
            end_time = now_moscow
            
            if period == 'today':
                # Смена считается с 12:00 текущего дня. Если сейчас раньше 12, то берем вчерашний день.
                if now_moscow.hour < 12: 
                    start_time = (now_moscow - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
                else: 
                    start_time = now_moscow.replace(hour=12, minute=0, second=0, microsecond=0)
            elif period == 'week': 
                start_time = now_moscow - datetime.timedelta(days=7)
            elif period == 'month': 
                start_time = now_moscow - datetime.timedelta(days=30)
            else: 
                return
                
            send_report(bot, call.message.chat.id, start_time, end_time)
