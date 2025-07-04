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
    # === ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ===
    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "С возвращением! Рады видеть вас снова. 😉\n\nЕсли ищешь ссылку на наш канал, просто отправь команду /channel.")
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            get_gift_button = types.KeyboardButton("🎁 ПОЛУЧИТЬ НАСТОЙКУ")
            keyboard.add(get_gift_button)
            bot.send_message(message.chat.id, 
                             "Привет! 👋 Нажми на кнопку ниже, чтобы получить свой подарок.", 
                             reply_markup=keyboard)

    @bot.message_handler(commands=['channel'])
    def handle_channel_command(message):
        keyboard = types.InlineKeyboardMarkup()
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        url_button = types.InlineKeyboardButton(text="➡️ Перейти на канал", url=channel_url)
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Вот ссылка на наш основной канал:", reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == "🎁 ПОЛУЧИТЬ НАСТОЙКУ")
    def handle_get_gift_press(message: types.Message):
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.send_message(user_id, "Вижу, ты уже наш подписчик! Спасибо тебе за это. ❤️")
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
                bot.answer_callback_query(call.id, "Похоже, вы еще не подписались. Попробуйте снова.", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "redeem_reward")
    def handle_redeem_reward(call: types.CallbackQuery):
        user_id = call.from_user.id
        if redeem_reward(user_id):
            final_text = "✅ Награда получена! Спасибо, что вы с нами. 😉"
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
        keyboard = types.InlineKeyboardMarkup()
        report_button = types.InlineKeyboardButton("📊 Сформировать отчет за текущую смену", callback_data="admin_report")
        keyboard.add(report_button)
        bot.send_message(message.chat.id, "👑 Админ-панель", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_callbacks(call: types.CallbackQuery):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔️ Доступ запрещен.")
            return
        action = call.data.split('_')[1]
        if action == 'report':
            bot.answer_callback_query(call.id, "Формирую отчет...")
            send_manual_report(bot, call.message.chat.id)

    # === СКРЫТАЯ КОМАНДА ДЛЯ ПЛАНИРОВЩИКА ===
    @bot.message_handler(commands=['send_daily_report'])
    def handle_send_report_command(message):
        send_scheduled_report(bot)

# === Вспомогательные функции ===
def issue_coupon(bot, user_id, username, first_name, chat_id):
    status = get_reward_status(user_id)
    if status in ['issued', 'redeemed']: return
    add_new_user(user_id, username or "N/A", first_name)
    coupon_text = ("🎉 Поздравляем! 🎉\n\n"
                   "Вы получили фирменную настойку!\n\n"
                   "**ВАЖНО:** Не нажимайте кнопку самостоятельно!\n"
                   "1. Покажите этот экран бармену.\n"
                   "2. Нажмите кнопку **только** по его просьбе.")
    redeem_keyboard = types.InlineKeyboardMarkup()
    redeem_button = types.InlineKeyboardButton(text="🔒 Награда заблокирована (нажать при бармене)", callback_data="redeem_reward")
    redeem_keyboard.add(redeem_button)
    try:
        bot.send_sticker(chat_id, NASTOYKA_STICKER_ID)
    except Exception as e:
        logging.error(f"Не удалось отправить стикер-купон: {e}")
    bot.send_message(chat_id, coupon_text, parse_mode="Markdown", reply_markup=redeem_keyboard)

def generate_report_text(start_time, end_time, issued, redeemed):
    report_date = end_time.strftime('%d.%m.%Y')
    return (f"**#Отчет_ТГ_Настойка_за_Подписку ({report_date})**\n\n"
            f"**Период:** с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')}\n\n"
            f"✅ **Выдано купонов (подписалось):** {issued}\n"
            f"🥃 **Погашено (выпито настоек):** {redeemed}")

def send_scheduled_report(bot):
    """Формирует и отправляет отчет за прошедшую смену."""
    tz_moscow = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.datetime.now(tz_moscow)
    end_time = now_moscow.replace(hour=6, minute=0, second=0, microsecond=0)
    start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    
    issued, redeemed = get_report_data_for_period(start_time, end_time)
    report_text = generate_report_text(start_time, end_time, issued, redeemed)
    bot.send_message(REPORT_CHAT_ID, report_text, parse_mode="Markdown")

def send_manual_report(bot, chat_id):
    """Формирует и отправляет отчет за текущую смену."""
    tz_moscow = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.datetime.now(tz_moscow)
    end_time = now_moscow
    if now_moscow.hour < 12:
        start_time = (now_moscow - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    else:
        start_time = now_moscow.replace(hour=12, minute=0, second=0, microsecond=0)

    issued, redeemed = get_report_data_for_period(start_time, end_time)
    report_text = generate_report_text(start_time, end_time, issued, redeemed)
    bot.send_message(chat_id, report_text, parse_mode="Markdown")
