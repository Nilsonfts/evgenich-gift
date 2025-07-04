import logging
import datetime

# Основные компоненты библиотеки для создания Telegram-бота
from telebot import types

# Библиотека для работы с часовыми поясами, чтобы время было корректным
import pytz

# --- Подключение переменных и настроек из вашего файла config.py ---
from config import (
    CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, THANK_YOU_STICKER_ID,
    FRIEND_BONUS_STICKER_ID, ADMIN_IDS, REPORT_CHAT_ID, GOOGLE_SHEET_KEY, MENU_URL
)
# --- Подключение всех функций для работы с Google Таблицами из файла g_sheets.py ---
from g_sheets import (
    get_reward_status, add_new_user, update_status, delete_user,
    get_referrer_id_from_user, count_successful_referrals, mark_referral_bonus_claimed,
    get_report_data_for_period, get_stats_by_source, get_weekly_cohort_data, get_top_referrers,
    log_conversation_turn, get_conversation_history, get_daily_updates
)
# --- Подключение данных о меню из отдельных файлов для удобства редактирования ---
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA

# --- Подключение "мозга" нашего бота - функции для вызова нейросети ---
from ai_assistant import get_ai_recommendation

# =======================================================================
# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
# =======================================================================

# Временное хранилище в памяти для данных пошагового бронирования.
user_booking_data = {}


# =======================================================================
# === ГЛАВНАЯ ФУНКЦИЯ РЕГИСТРАЦИИ ОБРАБОТЧИКОВ ===
# =======================================================================

def register_handlers(bot):
    """
    Главная функция, которая "регистрирует" все обработчики команд и кнопок в боте.
    """

    # =======================================================================
    # === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    # =======================================================================
    
    def _cancel_booking(message: types.Message):
        """
        Внутренняя функция для логики отмены бронирования.
        """
        user_id = message.from_user.id
        if user_id in user_booking_data:
            del user_booking_data[user_id]
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            menu_button = types.KeyboardButton("📖 Меню")
            friend_button = types.KeyboardButton("🤝 Привести товарища")
            book_button = types.KeyboardButton("📍 Забронировать стол")
            ai_help_button = types.KeyboardButton("🗣 Спроси у Евгенича")
            keyboard.row(menu_button, friend_button)
            keyboard.row(ai_help_button, book_button)
            if user_id in ADMIN_IDS:
                restart_button = types.KeyboardButton("/restart")
                keyboard.row(restart_button)
            
            bot.send_message(user_id, "Бронирование отменено. Вы возвращены в главное меню.", reply_markup=keyboard)
        else:
            bot.reply_to(message, "Нет активного действия для отмены.")

    # =======================================================================
    # === ОСНОВНЫЕ ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ И КНОПКИ ===
    # =======================================================================

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """
        Обрабатывает команду /start.
        """
        logging.info(f"Пользователь {message.from_user.id} нажал /start с текстом: {message.text}")
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        
        if status == 'redeemed':
            logging.info(f"Пользователь {user_id} уже получал награду. Показываем основное меню.")
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            menu_button = types.KeyboardButton("📖 Меню")
            friend_button = types.KeyboardButton("🤝 Привести товарища")
            book_button = types.KeyboardButton("📍 Забронировать стол")
            ai_help_button = types.KeyboardButton("🗣 Спроси у Евгенича")
            
            keyboard.row(menu_button, friend_button)
            keyboard.row(ai_help_button, book_button)

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

        if status == 'not_found':
            logging.info(f"Новый пользователь {user_id}. Регистрируем...")
            referrer_id = None
            source = 'direct'
            
            args = message.text.split(' ', 1)
            
            if len(args) > 1:
                payload = args[1]
                logging.info(f"Обнаружена нагрузка (payload): {payload}")
                if payload.startswith('ref_'):
                    try:
                        referrer_id = int(payload.replace('ref_', ''))
                        source = 'Реферал'
                    except (ValueError, IndexError):
                        logging.warning(f"Не удалось распознать ref_id из {payload}")
                        pass
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

    @bot.message_handler(commands=['book'])
    @bot.message_handler(func=lambda message: message.text == "📍 Забронировать стол")
    def handle_booking_info(message: types.Message):
        """
        Запускает интерактивный сценарий бронирования стола.
        """
        if user_booking_data.get(message.from_user.id):
            bot.reply_to(message, "Ты уже находишься в процессе бронирования. Пожалуйста, введи запрошенные данные или отмени командой /cancel.")
            return
        logging.info(f"Пользователь {message.from_user.id} нажал кнопку 'Забронировать стол', запускаем интерактивный сценарий.")
        _show_booking_options(message)

    @bot.message_handler(commands=['friend'])
    @bot.message_handler(func=lambda message: message.text == "🤝 Привести товарища")
    def handle_friend_command(message: types.Message):
        """
        Генерирует и отправляет пользователю его персональную реферальную ссылку.
        """
        if user_booking_data.get(message.from_user.id):
            bot.reply_to(message, "Товарищ, давай сначала закончим с бронью. Пожалуйста, введи запрошенные данные или отмени командой /cancel.")
            return

        user_id = message.from_user.id
        logging.info(f"Пользователь {user_id} запросил реферальную ссылку.")
        
        try:
            bot_username = bot.get_me().username
            if not bot_username:
                logging.error("ОШИБКА: У бота не установлен публичный username (@имя_бота). Реферальная ссылка не может быть создана. Зайдите в @BotFather, чтобы установить его.")
                bot.send_message(user_id, "Ошибка: Не удалось создать ссылку, так как у этого бота нет публичного имени (@username). Администратору необходимо настроить это в @BotFather.")
                return

            ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

            text_before = (
                "💪 Решил перевыполнить план, товарищ? Правильно!\n\n"
                "Вот твоя персональная директива на привлечение нового бойца. Отправь эту ссылку другу:"
            )
            bot.send_message(user_id, text_before, parse_mode="Markdown")

            # Отправляем ссылку отдельным сообщением
            bot.send_message(user_id, ref_link, disable_web_page_preview=True)

            text_after = (
                "Как только он пройдет все инстанции и получит свою настойку (и выдержит 'испытательный срок' в 24 часа), партия тебя отблагодарит **еще одной дефицитной настойкой**! 🥃\n\n"
                "*Помни, план — не более 5 товарищей.*"
            )
            bot.send_message(user_id, text_after, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"Критическая ошибка при создании реферальной ссылки для {user_id}: {e}", exc_info=True)
            bot.send_message(user_id, "Что-то пошло не так при создании ссылки. Пожалуйста, проверьте консоль бота для получения подробной информации об ошибке.")

    @bot.message_handler(commands=['channel'])
    def handle_channel_command(message: types.Message):
        """
        Отправляет пользователю ссылку на основной Telegram-канал заведения.
        """
        logging.info(f"Пользователь {message.from_user.id} запросил ссылку на канал.")
        keyboard = types.InlineKeyboardMarkup()
        channel_url = f"https.me/{CHANNEL_ID.lstrip('@')}"
        url_button = types.InlineKeyboardButton(text="➡️ Перейти на канал", url=channel_url)
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Вот ссылка на наш основной канал:", reply_markup=keyboard)

    @bot.message_handler(commands=['menu'])
    @bot.message_handler(func=lambda message: message.text == "📖 Меню")
    def handle_menu_command(message: types.Message):
        """
        Показывает пользователю кнопки для выбора меню.
        """
        if user_booking_data.get(message.from_user.id):
            bot.reply_to(message, "Товарищ, давай сначала закончим с бронью. Пожалуйста, введи запрошенные данные или отмени командой /cancel.")
            return
        logging.info(f"Пользователь {message.from_user.id} открыл меню.")
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        nastoiki_button = types.InlineKeyboardButton(text="🥃 Меню настоек", callback_data="menu_nastoiki_main")
        food_button = types.InlineKeyboardButton(text="🍔 Меню кухни", callback_data="menu_food_main")
        full_menu_button = types.InlineKeyboardButton(text="📄 Полное меню (Сайт)", url=MENU_URL)
        keyboard.add(nastoiki_button, food_button, full_menu_button)
        bot.send_message(message.chat.id, "Чего желаешь, товарищ? Настойку или закусить?", reply_markup=keyboard)

    @bot.message_handler(commands=['help'])
    def handle_help_command(message: types.Message):
        """
        Отправляет справочное сообщение с описанием команд бота.
        """
        user_id = message.from_user.id
        help_text = (
            "**Инструкция по боту «Евгенич Настаивает»**\n\n"
            "Я — ваш партийный товарищ, который выдает дефицитный продукт (фирменную настойку) за подписку на наш канал.\n\n"
            "**Основные команды:**\n"
            "• `/start` - Начать диалог и получить талон на настойку.\n"
            "• `/menu` - Посмотреть меню нашего заведения.\n"
            "• `/book` - Забронировать стол.\n"
            "• `/cancel` - Отменить текущее действие (например, бронирование).\n"
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
        
    @bot.message_handler(commands=['cancel'])
    def handle_cancel_command(message: types.Message):
        """
        Обрабатывает команду /cancel для отмены текущего действия.
        """
        _cancel_booking(message)

    @bot.message_handler(func=lambda message: message.text == "🗣 Спроси у Евгенича")
    def handle_ai_prompt_button(message: types.Message):
        """
        Обрабатывает нажатие на кнопку-подсказку для ИИ.
        """
        if user_booking_data.get(message.from_user.id):
            bot.reply_to(message, "Товарищ, давай сначала закончим с бронью. Пожалуйста, введи запрошенные данные или отмени командой /cancel.")
            return
        bot.reply_to(message, "Смело пиши мне свои пожелания! Например: «посоветуй что-нибудь сладкое и сливочное» или «ищу самую ядрёную настойку».")

    @bot.message_handler(func=lambda message: message.text == "🥃 Получить настойку по талону")
    def handle_get_gift_press(message: types.Message):
        """
        Запускает воронку получения настойки за подписку.
        """
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

    # =======================================================================
    # === ОБРАБОТЧИКИ НАЖАТИЙ НА INLINE-КНОПКИ (CALLBACKS) ===
    # =======================================================================

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        """
        Проверяет подписку на канал.
        """
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
        """
        Обрабатывает погашение купона на настойку.
        """
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
            book_button = types.KeyboardButton("📍 Забронировать стол")
            ai_help_button = types.KeyboardButton("🗣 Спроси у Евгенича")
            final_keyboard.row(menu_button, friend_button)
            final_keyboard.row(ai_help_button, book_button)
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
                logging.info(f"Пользователь {user_id} погасил награду. Планировщик должен его проверить для реферера {referrer_id} через 24ч.")
        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "menu_nastoiki_main")
    def callback_menu_nastoiki_main(call: types.CallbackQuery):
        """Показывает главное меню с категориями настоек."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(text=category['title'], callback_data=f"menu_category_{index}") for index, category in enumerate(MENU_DATA)]
        keyboard.add(*buttons)
        try:
            bot.edit_message_text(
                "**Меню настоек «Евгенич»**\n\nВыберите категорию:",
                call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown"
            )
        except Exception:
            bot.send_message(call.message.chat.id, "**Меню настоек «Евгенич»**\n\nВыберите категорию:", reply_markup=keyboard, parse_mode="Markdown")
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
            text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "menu_food_main")
    def callback_menu_food_main(call: types.CallbackQuery):
        """Показывает главное меню с категориями кухни."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(text=category, callback_data=f"food_category_{category}") for category in FOOD_MENU_DATA.keys()]
        keyboard.add(*buttons)
        bot.edit_message_text(
            "**Меню Кухни**\n\nВыбирай, чем будешь закусывать:",
            call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("food_category_"))
    def callback_food_category(call: types.CallbackQuery):
        """Показывает список блюд в выбранной категории."""
        category_name = call.data.replace("food_category_", "")
        category_items = FOOD_MENU_DATA.get(category_name, [])
        text = f"**{category_name}**\n\n"
        for item in category_items:
            text += f"• {item['name']} - **{item['price']}₽**\n"
        keyboard = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям кухни", callback_data="menu_food_main")
        keyboard.add(back_button)
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
        
    # =======================================================================
    # === ЛОГИКА ПОШАГОВОГО БРОНИРОВАНИЯ (FINITE STATE MACHINE) ===
    # =======================================================================
    
    def _show_booking_options(message):
        """Шаг 1: Показывает пользователю кнопки с вариантами бронирования."""
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📞 Позвонить", callback_data="booking_phone"),
            types.InlineKeyboardButton("🌐 Забронировать через сайт", callback_data="booking_site"),
            types.InlineKeyboardButton("🔐 Написать в секретный чат", callback_data="booking_secret"),
            types.InlineKeyboardButton("🤖 Забронировать через меня", callback_data="booking_bot")
        )
        bot.send_message(message.chat.id, "Конечно, товарищ! Как будем действовать?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("booking_"))
    def handle_booking_option(call: types.CallbackQuery):
        """Шаг 2: Обрабатывает выбор пользователя и запускает сбор данных."""
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

        if call.data == "booking_phone":
            bot.send_message(call.message.chat.id, "📞 Звони по номеру: `8 (812) 317-23-53`", parse_mode="Markdown")
        elif call.data == "booking_site":
            bot.send_message(call.message.chat.id, "🌐 Вот ссылка для самостоятельной брони: https://evgenichspb.restoplace.ws/")
        elif call.data == "booking_secret":
            keyboard = types.InlineKeyboardMarkup()
            url_button = types.InlineKeyboardButton(text="👉 Перейти в секретный чат", url="https://t.me/stolik_evgenicha")
            keyboard.add(url_button)
            text = (
                "От сердца отрываю, товарищ! 🤫\n\n"
                "Это наш секретный чат для броней, только для своих. А ты теперь свой. "
                "Смело жми на кнопку и пиши туда."
            )
            bot.send_message(call.message.chat.id, text, reply_markup=keyboard)
        elif call.data == "booking_bot":
            prompt_text = (
                "Отлично! Как тебя звать, товарищ?\n\n"
                "*Чтобы отменить, в любой момент напиши /cancel*"
            )
            msg = bot.send_message(call.message.chat.id, prompt_text, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_name_step)

    def process_name_step(message):
        if message.text == '/cancel':
            return _cancel_booking(message)
        user_id = message.from_user.id
        user_booking_data[user_id] = {'name': message.text}
        msg = bot.send_message(message.chat.id, "Записал. Когда хочешь заглянуть в рюмочную? (Дата)")
        bot.register_next_step_handler(msg, process_date_step)

    def process_date_step(message):
        if message.text == '/cancel':
            return _cancel_booking(message)
        user_id = message.from_user.id
        user_booking_data[user_id]['date'] = message.text
        msg = bot.send_message(message.chat.id, "Принято. Во сколько подходишь? (Время)")
        bot.register_next_step_handler(msg, process_time_step)

    def process_time_step(message):
        if message.text == '/cancel':
            return _cancel_booking(message)
        user_id = message.from_user.id
        user_booking_data[user_id]['time'] = message.text
        msg = bot.send_message(message.chat.id, "Сколько вас будет — чтобы чебуреков хватило на всех! (Кол-во гостей)")
        bot.register_next_step_handler(msg, process_guests_step)

    def process_guests_step(message):
        if message.text == '/cancel':
            return _cancel_booking(message)
        user_id = message.from_user.id
        user_booking_data[user_id]['guests'] = message.text
        msg = bot.send_message(message.chat.id, "Телефончик оставь, а то в 80-х без номерка даже кассеты не выдавали.")
        bot.register_next_step_handler(msg, process_phone_step)

    def process_phone_step(message):
        if message.text == '/cancel':
            return _cancel_booking(message)
        user_id = message.from_user.id
        user_booking_data[user_id]['phone'] = message.text
        msg = bot.send_message(message.chat.id, "И последнее: повод душевный или торжественный?")
        bot.register_next_step_handler(msg, process_reason_step)

    def process_reason_step(message):
        if message.text == '/cancel':
            return _cancel_booking(message)
        user_id = message.from_user.id
        user_booking_data[user_id]['reason'] = message.text
        data = user_booking_data.get(user_id, {})
        confirmation_text = (
            "Всё верно, товарищ?\n\n"
            f"📌 Имя: {data.get('name', 'не указано')}\n"
            f"📆 Дата: {data.get('date', 'не указано')}\n"
            f"🕒 Время: {data.get('time', 'не указано')}\n"
            f"👥 Гостей: {data.get('guests', 'не указано')}\n"
            f"☎️ Телефон: {data.get('phone', 'не указано')}\n"
            f"🎉 Повод: {data.get('reason', 'не указано')}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Всё верно!", callback_data="confirm_booking"))
        markup.add(types.InlineKeyboardButton("❌ Начать заново", callback_data="cancel_booking"))
        bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_booking", "cancel_booking"])
    def handle_booking_confirmation(call: types.CallbackQuery):
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

        if call.data == "confirm_booking":
            data = user_booking_data.get(user_id, {})
            final_text = (
                "🚨 Новая бронь:\n\n"
                f"Имя: {data.get('name', 'не указано')}\n"
                f"Дата: {data.get('date', 'не указано')}\n"
                f"Время: {data.get('time', 'не указано')}\n"
                f"Гости: {data.get('guests', 'не указано')}\n"
                f"Телефон: {data.get('phone', 'не указано')}\n"
                f"Повод: {data.get('reason', 'не указано')}"
            )
            bot.send_message(REPORT_CHAT_ID, final_text)
            bot.send_message(user_id, "Я всё записал в блокнот. Передам лично. Ну ты даёшь!")
            if user_id in user_booking_data:
                del user_booking_data[user_id]
        elif call.data == "cancel_booking":
            if user_id in user_booking_data:
                del user_booking_data[user_id]
            prompt_text = (
                "Без проблем, товарищ. Начнем сначала. Как тебя звать?\n\n"
                "*Чтобы отменить, в любой момент напиши /cancel*"
            )
            msg = bot.send_message(user_id, prompt_text, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_name_step)

    # =======================================================================
    # === АДМИН-ПАНЕЛЬ И ПРОЧИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    # =======================================================================

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
        elif action == 'admin_menu_reports':
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            today_report_button = types.InlineKeyboardButton("📊 Отчет за текущую смену", callback_data="admin_report_today")
            week_report_button = types.InlineKeyboardButton("📅 Отчет за неделю", callback_data="admin_report_week")
            month_report_button = types.InlineKeyboardButton("🗓️ Отчет за месяц", callback_data="admin_report_month")
            back_button = types.InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="admin_menu_main")
            keyboard.add(today_report_button, week_report_button, month_report_button, back_button)
            bot.edit_message_text("**Меню отчетов**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
        elif action == 'admin_menu_analytics':
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            source_button = types.InlineKeyboardButton("По источникам", callback_data="admin_action_sources")
            cohort_button = types.InlineKeyboardButton("Когорты по неделям", callback_data="admin_action_cohorts")
            back_button = types.InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="admin_menu_main")
            keyboard.add(source_button, cohort_button, back_button)
            bot.edit_message_text("**Меню аналитики**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
        elif action == 'admin_action_leaderboard':
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

    # =======================================================================
    # === ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ К ИИ (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ) ===
    # =======================================================================
    @bot.message_handler(func=lambda message: True, content_types=['text'])
    def handle_ai_query(message: types.Message):
        user_id = message.from_user.id
        user_text = message.text

        if user_booking_data.get(user_id):
            return
        
        known_buttons = ['📖 Меню', '🤝 Привести товарища', '🗣 Спроси у Евгенича', '🥃 Получить настойку по талону', '📍 Забронировать стол']
        if user_text in known_buttons or user_text.startswith('/'):
            return 
        
        log_conversation_turn(user_id, "user", user_text)
        history = get_conversation_history(user_id, limit=6)
        
        bot.send_chat_action(message.chat.id, 'typing')

        ai_response = get_ai_recommendation(user_text, history)
        
        if "[START_BOOKING_FLOW]" in ai_response:
            _show_booking_options(message)
            log_conversation_turn(user_id, "assistant", "Предложил варианты бронирования.")
        else:
            log_conversation_turn(user_id, "assistant", ai_response)
            bot.reply_to(message, ai_response, parse_mode="Markdown")
