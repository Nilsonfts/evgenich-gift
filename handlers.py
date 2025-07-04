import logging
import datetime
from telebot import types
import pytz
from config import (
    CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, THANK_YOU_STICKER_ID,
    ADMIN_IDS, REPORT_CHAT_ID
)
from g_sheets import get_reward_status, add_new_user, redeem_reward, get_report_data_for_period

def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    # === ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ===
    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "С возвращением! Рады видеть вас снова. 😉\n\nЕсли ищешь ссылку на наш канал, просто отправь команду /channel.")
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            get_gift_button = types.KeyboardButton("🥃 Получить настойку по талону")
            keyboard.add(get_gift_button)
            bot.send_message(message.chat.id,
                             "Привет, товарищ! Готов обменять подписку на вкус детства?",
                             reply_markup=keyboard)

    @bot.message_handler(commands=['channel'])
    def handle_channel_command(message):
        keyboard = types.InlineKeyboardMarkup()
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        url_button = types.InlineKeyboardButton(text="➡️ Перейти на канал", url=channel_url)
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Вот ссылка на наш основной канал:", reply_markup=keyboard)

    @bot.message_handler(commands=['menu'])
    def handle_menu_command(message):
        keyboard = types.InlineKeyboardMarkup()
        url_button = types.InlineKeyboardButton(text="📖 Открыть меню бара", url="https://spb.evgenich.bar/menu")
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Наше меню всегда доступно по кнопке ниже:", reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == "🥃 Получить настойку по талону")
    def handle_get_gift_press(message: types.Message):
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.send_message(user_id, "Уважаю — подписался! Получай гостинец.")
                issue_coupon(bot, user_id, message.from_user.username, message.from_user.first_name, message.chat.id)
                return
        except Exception as e:
            logging.error(f"Ошибка при предварительной проверке подписки для {user_id}: {e}")
        welcome_text = ("Отлично! 👍\n\n"
                        "Чтобы получить настойку, подпишись на наш телеграм-канал. Это займет всего секунду.\n\n"
                        "Когда подпишешься — нажимай на кнопку «Я подписался» здесь же.")
        inline_keyboard = types.InlineKeyboardMarkup(row_width=1)
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        subscribe_button = types.InlineKeyboardButton(text="➡️ Перейти к каналу", url=channel_url)
        check_button = types.InlineKeyboardButton(text="✅ Я подписался, проверить!", callback_data="check_subscription")
        inline_keyboard.add(subscribe_button, check_button)
        try:
            bot.send_sticker(message.chat.id, HELLO_STICKER_ID)
        except Exception as e:
            logging.error(f"Не удалось отправить приветственный стикер: {e}")
        bot.send_message(message.chat.id, welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        user_id = call.from_user.id
        bot.answer_callback_query(call.id, text="Проверяю вашу подписку...")
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.delete_message(call.message.chat.id, call.message.message_id)
                issue_coupon(bot, user_id, call.from_user.username, call.from_user.first_name, call.message.chat.id)
            else:
                bot.answer_callback_query(call.id, "Ну куда без подписки, родной? Там всё по-честному.", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "redeem_reward")
    def handle_redeem_reward(call: types.CallbackQuery):
        user_id = call.from_user.id
        if redeem_reward(user_id):
            final_text = ("✅ Ну вот и бахнули!\n\n"
                          "Между первой и второй, как известно, перерывчик небольшой…\n"
                          "🍷 Ждём тебя за следующей!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, final_text)
            try:
                bot.send_sticker(call.message.chat.id, THANK_YOU_STICKER_ID)
            except Exception as e:
                logging.error(f"Не удалось отправить прощальный стикер: {e}")
        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)

    # === АДМИН-ПАНЕЛЬ ===
    @bot.message_handler(commands=['admin'])
    def handle_admin(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            bot.reply_to(message, "⛔️ Доступ запрещен.")
            return
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        today_report_button = types.InlineKeyboardButton("📊 Отчет за текущую смену", callback_data="admin_report_today")
        week_report_button = types.InlineKeyboardButton("📅 Отчет за неделю", callback_data="admin_report_week")
        month_report_button = types.InlineKeyboardButton("🗓️ Отчет за месяц", callback_data="admin_report_month")
        keyboard.add(today_report_button, week_report_button, month_report_button)
        bot.send_message(message.chat.id, "👑 Админ-панель", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_report'))
    def handle_admin_report_callbacks(call: types.CallbackQuery):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔️ Доступ запрещен.")
            return
        
        period = call.data.split('_')[-1]
        bot.answer_callback_query(call.id, f"Формирую отчет...")
        
        tz_moscow = pytz.timezone('Europe/Moscow')
        now_moscow = datetime.datetime.now(tz_moscow)
        end_time = now_moscow

        if period == 'today':
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

    # === СКРЫТАЯ КОМАНДА ДЛЯ ПЛАНИРОВЩИКА ===
    @bot.message_handler(commands=['send_daily_report'])
    def handle_send_report_command(message):
        tz_moscow = pytz.timezone('Europe/Moscow')
        now_moscow = datetime.datetime.now(tz_moscow)
        end_time = now_moscow.replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        send_report(bot, REPORT_CHAT_ID, start_time, end_time)

# === Вспомогательные функции (вынесены за пределы register_handlers) ===
def issue_coupon(bot, user_id, username, first_name, chat_id):
    status = get_reward_status(user_id)
    if status in ['issued', 'redeemed']: return
    add_new_user(user_id, username or "N/A", first_name)
    coupon_text = ("🎉 Гражданин-товарищ, поздравляем!\n\n"
                   "Тебе досталась фирменная настойка «Евгенич» — почти как путёвка в пионерлагерь, только повеселее.\n\n"
                   "Что делать — коротко и ясно:\n"
                   "1. Покажи этот экран бармену-дежурному.\n"
                   "2. По его сигналу жми кнопку внизу — и сразу получаешь стопку!")
    redeem_keyboard = types.InlineKeyboardMarkup()
    redeem_button = types.InlineKeyboardButton(text="🔒 НАЛИТЬ ПРИ БАРМЕНЕ", callback_data="redeem_reward")
    redeem_keyboard.add(redeem_button)
    try:
        bot.send_sticker(chat_id, NASTOYKA_STICKER_ID)
    except Exception as e:
        logging.error(f"Не удалось отправить стикер-купон: {e}")
    bot.send_message(chat_id, coupon_text, parse_mode="Markdown", reply_markup=redeem_keyboard)

def generate_report_text(start_time, end_time, issued, redeemed, redeemed_users):
    """Генерирует текст отчета на основе данных."""
    if issued > 0:
        conversion_rate = round((redeemed / issued) * 100, 1)
    else:
        conversion_rate = 0
    
    report_date = end_time.strftime('%d.%m.%Y')
    header = f"**#Настойка_за_Подписку ({report_date})**\n\n"
    period_str = f"**Период:** с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')}\n\n"
    stats = (f"✅ **Выдано купонов:** {issued}\n"
             f"🥃 **Погашено настоек:** {redeemed}\n"
             f"📈 **Конверсия:** {conversion_rate}%\n")
    
    users_str = ""
    if redeemed_users:
        users_str += "\n**Настойку получили:**\n"
        for user in redeemed_users[:10]:
            users_str += f"• {user}\n"
        if len(redeemed_users) > 10:
            users_str += f"...и еще {len(redeemed_users) - 10}."
    return header + period_str + stats + users_str

def send_report(bot, chat_id, start_time, end_time):
    """Формирует и отправляет отчет в указанный чат."""
    try:
        issued, redeemed, redeemed_users = get_report_data_for_period(start_time, end_time)
        report_text = generate_report_text(start_time, end_time, issued, redeemed, redeemed_users)
        bot.send_message(chat_id, report_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")
