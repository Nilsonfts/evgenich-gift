# /handlers/admin_panel.py

import logging
import datetime
from telebot import types
from telebot.apihelper import ApiTelegramException
import pytz

# Импортируем всё необходимое
from config import ADMIN_IDS
import database
import texts
import keyboards
import settings_manager

# --- Вспомогательные функции для отчетов ---
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
    header = f"📊 **ОтчетПодпискаТГ ({report_date})** 📊\n\n"
    
    period_str = f"**Период:** с {start_time.strftime('%H:%M %d.%m')} по {end_time.strftime('%H:%M %d.%m')}\n\n"
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
            
    return header + period_str + stats + sources_str


def send_report(bot, chat_id, start_time, end_time):
    """Запрашивает данные из ЛОКАЛЬНОЙ БД и отправляет отчет."""
    try:
        issued, redeemed, redeemed_users, sources, total_redeem_time = database.get_report_data_for_period(start_time, end_time)
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

    # --- ИЗМЕНЕНИЕ: Ловим нажатие кнопки по тексту, а не по команде ---
    @bot.message_handler(func=lambda message: message.text == "👑 Админка")
    def handle_admin_command(message: types.Message):
        if not is_admin(message.from_user.id):
            # Эта проверка на всякий случай, т.к. кнопку и так видят только админы
            return
        
        current_settings = settings_manager.get_all_settings()
        bot.send_message(
            message.chat.id,
            texts.BOSS_MAIN_MENU,
            reply_markup=keyboards.get_boss_main_keyboard(current_settings),
            parse_mode="Markdown"
        )

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('admin_', 'boss_')))
    def handle_admin_callbacks(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, texts.ADMIN_ACCESS_DENIED, show_alert=True)
            return
        
        action = call.data

        try:
            bot.answer_callback_query(call.id) # Отвечаем на колбэк сразу
            
            if action == 'admin_report_manual_daily':
                bot.answer_callback_query(call.id, text="Формирую отчет за 24 часа...")
                tz_moscow = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(tz_moscow)
                start_time = end_time - datetime.timedelta(days=1)
                send_report(bot, call.message.chat.id, start_time, end_time)

            elif action.startswith('boss_toggle_'):
                feature_path = action.replace('boss_toggle_', '')
                current_value = settings_manager.get_setting(feature_path)
                settings_manager.update_setting(feature_path, not current_value)
                
                new_settings = settings_manager.get_all_settings()
                bot.edit_message_reply_markup(
                    call.message.chat.id, call.message.message_id,
                    reply_markup=keyboards.get_boss_main_keyboard(new_settings) # Обновляем главное меню
                )

            elif action == 'boss_upload_audio':
                bot.delete_message(call.message.chat.id, call.message.message_id)
                msg = bot.send_message(call.message.chat.id, "Отправь мне аудиофайл (как голосовое сообщение или файл .mp3/.ogg) для приветствия.")
                bot.register_next_step_handler(msg, process_audio_upload_step)

            elif action == 'boss_set_password':
                bot.delete_message(call.message.chat.id, call.message.message_id)
                msg = bot.send_message(call.message.chat.id, texts.BOSS_ASK_PASSWORD_WORD)
                bot.register_next_step_handler(msg, process_password_word_step)
            
            elif action == 'admin_report_leaderboard':
                top_list = database.get_top_referrers_for_month(5)
                if not top_list:
                    bot.send_message(call.message.chat.id, "В этом месяце пока никто не привел друзей, которые бы получили настойку.")
                    return
                month_name = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%B %Y')
                response = f"🏆 **Ударники труда за {month_name}**:\n(учитываются только друзья, погасившие настойку в этом месяце)\n\n"
                medals = ["🥇", "🥈", "🥉", "4.", "5."]
                for i, (name, count) in enumerate(top_list):
                    response += f"{medals[i]} Товарищ **{name}** — {count} чел.\n"
                bot.send_message(call.message.chat.id, response, parse_mode="Markdown")

        except ApiTelegramException as e:
            logging.warning(f"Не удалось обработать колбэк в админ-панели: {e}")

    # --- Пошаговые обработчики ---
    def process_audio_upload_step(message: types.Message):
        if not is_admin(message.from_user.id): return
        if message.audio:
            file_id = message.audio.file_id
            settings_manager.update_setting("greeting_audio_id", file_id)
            bot.reply_to(message, "✅ Аудио-приветствие сохранено! Теперь его можно вызывать командой /voice.")
            logging.info(f"Админ {message.from_user.id} загрузил новое аудио-приветствие. File ID: {file_id}")
        else:
            bot.reply_to(message, "Это не аудиофайл. Попробуй еще раз через админ-панель.")

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
