import logging
import datetime
from telebot import types
import pytz

# --- ИЗМЕНЕННЫЙ КОД: Добавлены новые импорты ---
from config import (
    CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, THANK_YOU_STICKER_ID,
    FRIEND_BONUS_STICKER_ID, ADMIN_IDS, REPORT_CHAT_ID, GOOGLE_SHEET_KEY, MENU_URL
)
from g_sheets import (
    get_reward_status, add_new_user, update_status, delete_user,
    get_referrer_id_from_user, count_successful_referrals, mark_referral_bonus_claimed,
    get_report_data_for_period, get_stats_by_source, get_weekly_cohort_data, get_top_referrers,
    get_sheet
)
# --- НОВЫЙ КОД: Импорты для меню и ИИ ---
from menu_nastoiki import MENU_DATA
from ai_assistant import get_ai_recommendation


def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    # === ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ===
    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        
        # Сценарий для пользователя, который УЖЕ получил настойку
        if status == 'redeemed':
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            menu_button = types.KeyboardButton("📖 Меню")
            friend_button = types.KeyboardButton("🤝 Привести товарища")
            ai_help_button = types.KeyboardButton("🤖 Что мне выпить?")
            
            keyboard.row(menu_button, friend_button)
            keyboard.row(ai_help_button)

            if user_id in ADMIN_IDS:
                restart_button = types.KeyboardButton("/restart")
                keyboard.row(restart_button)
            
            info_text = (
                "С возвращением, товарищ! Рады видеть снова. 😉\n\n"
                "Нажимай «📖 Меню» для просмотра или **просто напиши мне в чат, чего бы тебе хотелось** "
                "(например: _«хочу что-нибудь кислое и ягодное»_), и я помогу с выбором!"
            )
            bot.send_message(user_id, info_text, reply_markup=keyboard, parse_mode="Markdown")
            return

        # Сценарий для пользователя, который еще НЕ получал настойку (not_found, registered, issued)
        if status == 'not_found':
            referrer_id = None
            source = 'direct'
            args = message.text.split()
            if len(args) > 1:
                payload = args[1]
                if payload.startswith('ref_'):
                    try:
                        referrer_id = int(payload.replace('ref_', ''))
                        source = 'Реферал'
                    except (ValueError, IndexError): pass
                else:
                    allowed_sources = {'qr_tv': 'QR с ТВ', 'qr_bar': 'QR на баре', 'qr_toilet': 'QR в туалете', 'vk': 'VK', 'inst': 'Instagram', 'flyer': 'Листовки', 'site': 'Сайт'}
                    if payload in allowed_sources:
                        source = allowed_sources[payload]
            
            add_new_user(user_id, message.from_user.username or "N/A", message.from_user.first_name, source, referrer_id)
            if referrer_id:
                bot.send_message(user_id, "🤝 Привет, товарищ! Вижу, тебя направил сознательный гражданин. Проходи, не стесняйся.")

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        gift_button = types.KeyboardButton("🥃 Получить настойку по талону")
        keyboard.add(gift_button)
        bot.send_message(message.chat.id, "👋 Здравствуй, товарищ! Партия дает тебе уникальный шанс: обменять подписку на дефицитный продукт — фирменную настойку «Евгенич»! Жми на кнопку, не тяни.", reply_markup=keyboard)

    @bot.message_handler(commands=['friend'])
    @bot.message_handler(func=lambda message: message.text == "🤝 Привести товарища")
    def handle_friend_command(message: types.Message):
        user_id = message.from_user.id
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = (
            "💪 Решил перевыполнить план, товарищ? Правильно!\n\n"
            "Вот твоя персональная директива на привлечение нового бойца. Нажми на ссылку ниже, чтобы скопировать:\n"
            f"`{ref_link}`\n\n"
            "Отправь ее другу. Как только он пройдет все инстанции и получит свою настойку (и выдержит 'испытательный срок' в 24 часа), партия тебя отблагодарит **еще одной дефицитной настойкой**! 🥃\n\n"
            "*Помни, план — не более 5 товарищей.*"
        )
        bot.send_message(user_id, text, parse_mode="Markdown")

    @bot.message_handler(commands=['channel'])
    def handle_channel_command(message: types.Message):
        keyboard = types.InlineKeyboardMarkup()
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        url_button = types.InlineKeyboardButton(text="➡️ Перейти на канал", url=channel_url)
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Вот ссылка на наш основной канал:", reply_markup=keyboard)

    # --- ИЗМЕНЕННЫЙ КОД: Обработчик меню теперь предлагает выбор ---
    @bot.message_handler(commands=['menu'])
    @bot.message_handler(func=lambda message: message.text == "📖 Меню")
    def handle_menu_command(message: types.Message):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        nastoiki_button = types.InlineKeyboardButton(text="🥃 Меню настоек (Интерактивное)", callback_data="menu_nastoiki_main")
        full_menu_button = types.InlineKeyboardButton(text="📖 Полное меню бара (Сайт)", url=MENU_URL)
        keyboard.add(nastoiki_button, full_menu_button)
        bot.send_message(message.chat.id, "Выберите раздел меню, товарищ:", reply_markup=keyboard)

    @bot.message_handler(commands=['help'])
    def handle_help_command(message: types.Message):
        user_id = message.from_user.id
        help_text = (
            "**Инструкция по боту «Евгенич Настаивает»**\n\n"
            "Я — ваш партийный товарищ, который выдает дефицитный продукт (фирменную настойку) за подписку на наш канал.\n\n"
            "**Основные команды:**\n"
            "• `/start` - Начать диалог и получить талон на настойку.\n"
            "• `/menu` - Посмотреть меню нашего заведения.\n"
            "• `/channel` - Получить ссылку на наш основной Telegram-канал.\n"
            "• `/friend` - Получить персональную ссылку, чтобы пригласить друга и получить за это бонус.\n"
            "• `/help` - Показать это сообщение."
        )
        if user_id in ADMIN_IDS:
            admin_help_text = (
                "\n\n**👑 Административные команды:**\n"
                "• `/admin` - Открыть панель управления с отчетами.\n"
                "• `/restart` - Сбросить свой профиль для тестирования бота (осторожно!)."
            )
            help_text += admin_help_text
        bot.send_message(user_id, help_text, parse_mode="Markdown")

    # --- НОВЫЙ КОД: Обработчик кнопки-подсказки для ИИ ---
    @bot.message_handler(func=lambda message: message.text == "🤖 Что мне выпить?")
    def handle_ai_prompt_button(message: types.Message):
        bot.reply_to(message, "Смело пиши мне свои пожелания! Например: «посоветуй что-нибудь сладкое и сливочное» или «ищу самую ядрёную настойку».")

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

    # --- ИЗМЕНЕННЫЙ КОД: Обработчик для погашения награды теперь выдает новую клавиатуру и текст ---
    @bot.callback_query_handler(func=lambda call: call.data == "redeem_reward")
    def handle_redeem_reward(call: types.CallbackQuery):
        user_id = call.from_user.id
        if update_status(user_id, 'redeemed'):
            final_text = ("✅ Ну вот и бахнули!\n\n"
                          "Между первой и второй, как известно, перерывчик небольшой…\n"
                          "🍷 Ждём тебя за следующей!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, final_text)
            try:
                bot.send_sticker(call.message.chat.id, THANK_YOU_STICKER_ID)
            except Exception as e:
                logging.error(f"Не удалось отправить прощальный стикер: {e}")
            
            final_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            menu_button = types.KeyboardButton("📖 Меню")
            friend_button = types.KeyboardButton("🤝 Привести товарища")
            ai_help_button = types.KeyboardButton("🤖 Что мне выпить?")
            
            final_keyboard.row(menu_button, friend_button)
            final_keyboard.row(ai_help_button)

            if user_id in ADMIN_IDS:
                restart_button = types.KeyboardButton("/restart")
                final_keyboard.row(restart_button)
            
            info_text = (
                "Отлично! Теперь тебе доступны все возможности, товарищ.\n\n"
                "Нажимай «📖 Меню» для просмотра или **просто напиши мне в чат, чего бы тебе хотелось** "
                "(например: _«хочу что-нибудь кислое и ягодное»_), и я помогу с выбором!"
            )
            bot.send_message(user_id, info_text, reply_markup=final_keyboard, parse_mode="Markdown")

            referrer_id = get_referrer_id_from_user(user_id)
            if referrer_id:
                logging.info(f"Пользователь {user_id} погасил награду. Внешний планировщик должен будет его проверить для реферера {referrer_id} через 24ч.")
        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)

    # --- НОВЫЙ КОД: ОБРАБОТЧИКИ МЕНЮ НАСТОЕК ---
    @bot.callback_query_handler(func=lambda call: call.data == "menu_nastoiki_main")
    def callback_menu_nastoiki_main(call: types.CallbackQuery):
        """Показывает главное меню с категориями настоек."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for index, category in enumerate(MENU_DATA):
            buttons.append(
                types.InlineKeyboardButton(
                    text=category['title'],
                    callback_data=f"menu_category_{index}"
                )
            )
        keyboard.add(*buttons)
        try:
            bot.edit_message_text(
                "**Меню настоек «Евгенич»**\n\nВыберите категорию:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception: # Сообщение не изменилось, отправим новое
            bot.send_message(call.message.chat.id, "**Меню настоек «Еенич»**\n\nВыберите категорию:", reply_markup=keyboard, parse_mode="Markdown")
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("menu_category_"))
    def callback_menu_category(call: types.CallbackQuery):
        """Показывает список настоек в выбранной категории."""
        category_index = int(call.data.split("_")[2])
        category = MENU_DATA[category_index]

        text = f"**{category['title']}**\n_{category.get('category_narrative', '')}_\n\n"
        for item in category['items']:
            text += f"• **{item['name']}** — {item['price']}\n_{item['narrative_desc']}_\n\n"

        keyboard = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu_nastoiki_main")
        keyboard.add(back_button)

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)


    # === АДМИН-ПАНЕЛЬ ===
    @bot.message_handler(commands=['admin'])
    def handle_admin(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            bot.reply_to(message, "⛔️ Доступ запрещен.")
            return
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        reports_button = types.InlineKeyboardButton("📊 Стандартные отчеты", callback_data="admin_menu_reports")
        analytics_button = types.InlineKeyboardButton("📈 Глубокая аналитика", callback_data="admin_menu_analytics")
        leaderboard_button = types.InlineKeyboardButton("🏆 Доска почета вербовщиков", callback_data="admin_action_leaderboard")
        keyboard.add(reports_button, analytics_button, leaderboard_button)
        bot.send_message(message.chat.id, "👑 **Главное меню админ-панели**", reply_markup=keyboard, parse_mode="Markdown")

    @bot.message_handler(commands=['restart'])
    def handle_restart_command(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            return
        user_id = message.from_user.id
        success, response_message = delete_user(user_id)
        if success:
            bot.reply_to(message, f"✅ Успех: {response_message}\nМожете начинать тестирование заново, отправив команду /start.")
        else:
            bot.reply_to(message, f"❌ Ошибка при сбросе профиля: {response_message}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_callbacks(call: types.CallbackQuery):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔️ Доступ запрещен.")
            return
        
        action = call.data
        main_menu_text = "👑 **Главное меню админ-панели**"
        
        if action == 'admin_menu_main':
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            reports_button = types.InlineKeyboardButton("📊 Стандартные отчеты", callback_data="admin_menu_reports")
            analytics_button = types.InlineKeyboardButton("📈 Глубокая аналитика", callback_data="admin_menu_analytics")
            leaderboard_button = types.InlineKeyboardButton("🏆 Доска почета вербовщиков", callback_data="admin_action_leaderboard")
            keyboard.add(reports_button, analytics_button, leaderboard_button)
            try: bot.edit_message_text(main_menu_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
            except: pass
            return
        elif action == 'admin_menu_reports':
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            today_report_button = types.InlineKeyboardButton("📊 Отчет за текущую смену", callback_data="admin_report_today")
            week_report_button = types.InlineKeyboardButton("📅 Отчет за неделю", callback_data="admin_report_week")
            month_report_button = types.InlineKeyboardButton("🗓️ Отчет за месяц", callback_data="admin_report_month")
            back_button = types.InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="admin_menu_main")
            keyboard.add(today_report_button, week_report_button, month_report_button, back_button)
            bot.edit_message_text("**Меню отчетов**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
            return
        elif action == 'admin_menu_analytics':
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            source_button = types.InlineKeyboardButton("По источникам", callback_data="admin_action_sources")
            cohort_button = types.InlineKeyboardButton("Когорты по неделям", callback_data="admin_action_cohorts")
            back_button = types.InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="admin_menu_main")
            keyboard.add(source_button, cohort_button, back_button)
            bot.edit_message_text("**Меню аналитики**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
            return

        if action == 'admin_action_leaderboard':
            bot.answer_callback_query(call.id, "Составляю рейтинг...")
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
            bot.answer_callback_query(call.id, "Анализирую источники...")
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
            bot.answer_callback_query(call.id, "Сравниваю когорты...")
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
        
        elif call.data.startswith('admin_report'):
            period = call.data.split('_')[-1]
            tz_moscow = pytz.timezone('Europe/Moscow')
            now_moscow = datetime.datetime.now(tz_moscow)
            end_time = now_moscow
            if period == 'today':
                if now_moscow.hour < 12: start_time = (now_moscow - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
                else: start_time = now_moscow.replace(hour=12, minute=0, second=0, microsecond=0)
            elif period == 'week': start_time = now_moscow - datetime.timedelta(days=7)
            elif period == 'month': start_time = now_moscow - datetime.timedelta(days=30)
            else: return
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
            referred_user_id, referrer_id = int(parts[1]), int(parts[2])
            member = bot.get_chat_member(CHANNEL_ID, referred_user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                logging.info(f"Реферал {referred_user_id} отписался.")
                return
            if count_successful_referrals(referrer_id) >= 5:
                logging.info(f"Реферер {referrer_id} достиг лимита.")
                return
            bonus_text = ("✊ Товарищ! Твой друг проявил сознательность и остался в наших рядах. Партия тобой гордится!\n\n"
                          "Вот твой заслуженный бонус. Покажи это сообщение бармену, чтобы получить **еще одну фирменную настойку**.")
            if FRIEND_BONUS_STICKER_ID:
                try: bot.send_sticker(referrer_id, FRIEND_BONUS_STICKER_ID)
                except Exception as e: logging.error(f"Не удалось отправить стикер за друга: {e}")
            bot.send_message(referrer_id, bonus_text)
            mark_referral_bonus_claimed(referred_user_id)
            logging.info(f"Бонус за реферала {referred_user_id} успешно выдан {referrer_id}.")
        except Exception as e:
            logging.error(f"Ошибка при выполнении отложенной задачи по рефералам: {e}")

    # === Вспомогательные функции ===
    def issue_coupon(bot, user_id, username, first_name, chat_id):
        update_status(user_id, 'issued')
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
        try:
            issued, redeemed, redeemed_users, sources, total_redeem_time = get_report_data_for_period(start_time, end_time)
            if issued == 0:
                bot.send_message(chat_id, f"За период с {start_time.strftime('%d.%m %H:%M')} по {end_time.strftime('%d.%m %H:%M')} нет данных для отчета.")
                return
            report_text = generate_report_text(start_time, end_time, issued, redeemed, redeemed_users, sources, total_redeem_time)
            bot.send_message(chat_id, report_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить отчет в чат {chat_id}: {e}")

    # --- НОВЫЙ КОД: ОБРАБОТЧИК ЗАПРОСОВ К НЕЙРОСЕТИ (ДОЛЖЕН БЫТЬ В САМОМ КОНЦЕ) ---
    @bot.message_handler(func=lambda message: True, content_types=['text'])
    def handle_ai_query(message: types.Message):
        bot.send_chat_action(message.chat.id, 'typing')
        recommendation = get_ai_recommendation(message.text, MENU_DATA)
        bot.reply_to(message, recommendation, parse_mode="Markdown")
