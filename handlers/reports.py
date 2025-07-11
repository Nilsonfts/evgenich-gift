# /handlers/reports.py
"""
Модуль генерации и отправки отчетов для админ-панели.
"""
import pytz
import datetime
import logging
from telebot import types
import database
import texts
from .utils import shorten_name


def generate_daily_report_text(start_time, end_time, general_stats, staff_stats):
    # ...existing code from admin_panel.py...
    issued, redeemed, _, sources, total_redeem_time = general_stats
    _, left_count = database.get_daily_churn_data(start_time, end_time)
    # ...existing code...
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
    header = f"📊 **ОтчетПодпискаТГ ({report_date})** 📊\n\n"
    period_str = f"**Период:** с {start_time.strftime('%H:%M %d.%m')} по {end_time.strftime('%H:%M %d.%m')}\n\n"
    stats_block = (f"✅ **Выдано купонов:** {issued}\n"
                   f"🥃 **Погашено настоек:** {redeemed}\n"
                   f"📈 **Конверсия в погашение:** {conversion_rate}%\n"
                   f"⏱️ **Среднее время до погашения:** {avg_redeem_time_str}\n"
                   f"💔 **Отписалось за сутки:** {left_count} чел.\n"
                   f"🎯 **Удержание за сутки:** {retention_rate_str}\n")
    sources_block = ""
    if sources:
        sources_block += "\n---\n\n**Источники подписчиков (общие):**\n"
        filtered_sources = {k: v for k, v in sources.items() if not k.startswith("Сотрудник:")}
        sorted_sources = sorted(filtered_sources.items(), key=lambda item: item[1], reverse=True)
        for source, count in sorted_sources:
            sources_block += f"• {source}: {count}\n"
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

def send_report(bot, chat_id, start_time, end_time):
    try:
        general_stats = database.get_report_data_for_period(start_time, end_time)
        staff_stats = database.get_staff_performance_for_period(start_time, end_time)
        if general_stats[0] == 0:
            bot.send_message(chat_id, f"За период с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')} нет данных для отчета.")
            return
        report_text = generate_daily_report_text(start_time, end_time, general_stats, staff_stats)
        bot.send_message(chat_id, report_text, parse_mode="Markdown")
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
                bot.send_message(chat_id, winner_text)
    except Exception as e:
        logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")
        bot.send_message(chat_id, "Ошибка при формировании отчета.")
