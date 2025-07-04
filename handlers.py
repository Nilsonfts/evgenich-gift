import logging
import datetime
from telebot import types
import pytz
from config import (
    CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, THANK_YOU_STICKER_ID,
    FRIEND_BONUS_STICKER_ID, ADMIN_IDS, REPORT_CHAT_ID
)
from g_sheets import (
    get_reward_status, add_new_user, redeem_reward, delete_user,
    get_referrer_id_from_user, count_successful_referrals, mark_referral_bonus_claimed,
    get_report_data_for_period
)

def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    # === ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ===
    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        user_id = message.from_user.id
        referrer_id = None
        source = 'direct'

        args = message.text.split()
        if len(args) > 1:
            payload = args[1]
            if payload.startswith('ref_'):
                try:
                    referrer_id = int(payload.replace('ref_', ''))
                    source = 'Реферал'
                except (ValueError, IndexError):
                    pass
            else:
                allowed_sources = {'qr_tv': 'QR с ТВ', 'qr_bar': 'QR на баре', 'qr_toilet': 'QR в туалете', 'vk': 'VK', 'inst': 'Instagram', 'flyer': 'Листовки', 'site': 'Сайт'}
                if payload in allowed_sources:
                    source = allowed_sources[payload]

        if get_reward_status(user_id) == 'not_found':
            add_new_user(user_id, message.from_user.username or "N/A", message.from_user.first_name, source, referrer_id)
            if referrer_id:
                bot.send_message(user_id, "🤝 Привет, товарищ! Вижу, тебя направил сознательный гражданин. Проходи, не стесняйся. У нас тут почти коммунизм — первая бесплатно.")

        status = get_reward_status(user_id)
        
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        if status in ['issued', 'redeemed']:
            # Клавиатура для ВЕРНУВШЕГОСЯ пользователя
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            menu_button = types.KeyboardButton("📖 Меню")
            friend_button = types.KeyboardButton("🤝 Привести товарища")
            keyboard.row(menu_button, friend_button) # Четко указываем, что кнопки в одном ряду
            bot.send_message(user_id, "С возвращением! Рады видеть вас снова. 😉", reply_markup=keyboard)
        else:
            # Клавиатура для НОВОГО пользователя
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            gift_button = types.KeyboardButton("🥃 Получить настойку по талону")
            keyboard.add(gift_button) # Только одна кнопка
            bot.send_message(message.chat.id, "👋 Здравствуй, товарищ! Партия дает тебе уникальный шанс: обменять подписку на дефицитный продукт — фирменную настойку «Евгенич»! Жми на кнопку, не тяни.", reply_markup=keyboard)

    # ... (остальной код файла остается без изменений) ...
    # ... (я привожу его полностью ниже для твоего удобства) ...

    @bot.message_handler(commands=['friend'])
    @bot.message_handler(func=lambda message: message.text == "🤝 Привести товарища")
    def handle_friend_command(message: types.Message):
        user_id = message.from_user.id
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = (
            "💪 Решил перевыполнить план, товарищ? Правильно!\n\n"
            f"Вот твоя персональная директива на привлечение нового бойца:\n`{ref_link}`\n\n"
            "Отправь ее другу. Как только он пройдет все инстанции и получит свою настойку (и выдержит 'испытательный срок' в 24 часа), партия тебя отблагодарит дефицитной закуской! 🥖\n\n"
            "*Помни, план — не более 5 товарищей.*"
        )
        bot.send_message(user_id, text, parse_mode="Markdown")

    @bot.message_handler(commands=['channel'])
    def handle_channel_command(message: types.Message):
        keyboard = types.InlineKeyboardMarkup()
        channel_url = f"https.me/{CHANNEL_ID.lstrip('@')}"
        url_button = types.InlineKeyboardButton(text="➡️ Перейти на канал", url=channel_url)
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Вот ссылка на наш основной канал:", reply_markup=keyboard)

    @bot.message_handler(commands=['menu'])
    @bot.message_handler(func=lambda message: message.text == "📖 Меню")
    def handle_menu_command(message: types.Message):
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
        channel_url = f"https.me/{CHANNEL_ID.lstrip('@')}"
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
            
            referrer_id = get_referrer_id_from_user(user_id)
            if referrer_id:
                logging.info(f"Пользователь {user_id} погасил награду. Внешний планировщик должен будет его проверить для реферера {referrer_id} через 24ч.")
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

    @bot.message_handler(commands=['restart'])
    def handle_restart_command(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            return
        user_id = message.from_user.id
        if delete_user(user_id):
            bot.reply_to(message, "✅ Ваш профиль в боте сброшен. Можете начинать тестирование заново, отправив команду /start.")
        else:
            bot.reply_to(message, "🤔 Не удалось найти ваш профиль для сброса. Возможно, вы еще не взаимодействовали с ботом.")

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

    # === СКРЫТЫЕ КОМАНДЫ ДЛЯ ПЛАНИРОВЩИКА ===
    @bot.message_handler(commands=['send_daily_report'])
    def handle_send_report_command(message):
        tz_moscow = pytz.timezone('Europe/Moscow')
        now_moscow = datetime.datetime.now(tz_moscow)
        end_time = now_moscow.replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        send_report(bot, REPORT_CHAT_ID, start_time, end_time)

    @bot.message_handler(commands=['check_referral_and_give_bonus'])
    def handle_check_referral_command(message):
        try:
            parts = message.text.split()
            if len(parts) < 3: return
            referred_user_id = int(parts[1])
            referrer_id = int(parts[2])
            member = bot.get_chat_member(CHANNEL_ID, referred_user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                logging.info(f"Реферал {referred_user_id} отписался. Бонус для {referrer_id} не выдан.")
                return
            ref_count = count_successful_referrals(referrer_id)
            if ref_count >= 5:
                logging.info(f"Реферер {referrer_id} достиг лимита бонусов.")
                return
            bonus_text = ("✊ Товарищ! Твой друг проявил сознательность и остался в наших рядах. Партия тобой гордится!\n\n"
                          "Вот твой заслуженный бонус. Покажи это сообщение бармену, чтобы получить **фирменные гренки**.")
            if FRIEND_BONUS_STICKER_ID:
                try: bot.send_sticker(referrer_id, FRIEND_BONUS_STICKER_ID)
                except Exception as e: logging.error(f"Не удалось отправить стикер за друга: {e}")
            bot.send_message(referrer_id, bonus_text)
            mark_referral_bonus_claimed(referred_user_id)
            logging.info(f"Бонус за реферала {referred_user_id} успешно выдан {referrer_id}.")
        except Exception as e:
            logging.error(f"Ошибка при выполнении отложенной задачи по рефералам: {e}")

# === Вспомогательные функции (вынесены за пределы register_handlers) ===
def issue_coupon(bot, user_id, username, first_name, chat_id):
    status = get_reward_status(user_id)
    if status in ['issued', 'redeemed']: return
    if status == 'not_found':
        add_new_user(user_id, username or "N/A", first_name, 'direct')
    
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

def generate_report_text(start_time, end_time, issued, redeemed, redeemed_users, sources, total_redeem_time_seconds):
    """Генерирует текст 'супер-отчета' на основе данных."""
    conversion_rate = round((redeemed / issued) * 100, 1) if issued > 0 else 0
    avg_redeem_time_str = "н/д"
    if redeemed > 0:
        avg_seconds = total_redeem_time_seconds / redeemed
        hours = int(avg_seconds // 3600)
        minutes = int((avg_seconds % 3600) // 60)
        avg_redeem_time_str = f"{hours} ч {minutes} мин"
    report_date = end_time.strftime('%d.%m.%Y')
    header = f"**#Настойка_за_Подписку ({report_date})**\n\n"
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
    """Универсальная функция для отправки отчета."""
    try:
        issued, redeemed, redeemed_users, sources, total_redeem_time = get_report_data_for_period(start_time, end_time)
        if issued == 0:
            bot.send_message(chat_id, f"За период с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')} нет данных для отчета.")
            return
        report_text = generate_report_text(start_time, end_time, issued, redeemed, redeemed_users, sources, total_redeem_time)
        bot.send_message(chat_id, report_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")
