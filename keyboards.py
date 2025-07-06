# keyboards.py
from telebot import types
from config import ADMIN_IDS, MENU_URL
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA

# === ОСНОВНЫЕ REPLY-КЛАВИАТУРЫ ===

def get_main_menu_keyboard(user_id):
    """Возвращает главную клавиатуру для основного меню."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_button = types.KeyboardButton("📖 Меню")
    friend_button = types.KeyboardButton("🤝 Привести товарища")
    book_button = types.KeyboardButton("📍 Забронировать стол")
    ai_help_button = types.KeyboardButton("🗣 Спроси у Евгенича")
    
    keyboard.row(menu_button, friend_button)
    keyboard.row(ai_help_button, book_button)
    
    if user_id in ADMIN_IDS:
        admin_button = types.KeyboardButton("👑 админка")
        keyboard.row(admin_button)
        
    return keyboard

def get_gift_keyboard():
    """Возвращает клавиатуру для получения подарка."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    gift_button = types.KeyboardButton("🥃 Получить настойку по талону")
    keyboard.add(gift_button)
    return keyboard

# === INLINE-КЛАВИАТУРЫ ДЛЯ ПОДПИСКИ И ПОДАРКА ===

def get_subscription_keyboard(channel_url):
    """Возвращает клавиатуру для проверки подписки на канал."""
    inline_keyboard = types.InlineKeyboardMarkup(row_width=1)
    subscribe_button = types.InlineKeyboardButton(text="➡️ Перейти к каналу", url=channel_url)
    check_button = types.InlineKeyboardButton(text="✅ Я подписался, проверить!", callback_data="check_subscription")
    inline_keyboard.add(subscribe_button, check_button)
    return inline_keyboard

def get_redeem_keyboard():
    """Возвращает кнопку для погашения купона."""
    redeem_keyboard = types.InlineKeyboardMarkup()
    redeem_button = types.InlineKeyboardButton(text="🔒 НАЛИТЬ ПРИ БАРМЕНЕ", callback_data="redeem_reward")
    redeem_keyboard.add(redeem_button)
    return redeem_keyboard
    
# === INLINE-КЛАВИАТУРЫ ДЛЯ МЕНЮ ===

def get_menu_choice_keyboard():
    """Возвращает клавиатуру для выбора типа меню (настойки или кухня)."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    nastoiki_button = types.InlineKeyboardButton(text="🥃 Меню настоек", callback_data="menu_nastoiki_main")
    food_button = types.InlineKeyboardButton(text="🍔 Меню кухни", callback_data="menu_food_main")
    full_menu_button = types.InlineKeyboardButton(text="📄 Полное меню (Сайт)", url=MENU_URL)
    keyboard.add(nastoiki_button, food_button, full_menu_button)
    return keyboard

def get_nastoiki_categories_keyboard():
    """Возвращает клавиатуру с категориями настоек И КНОПКОЙ НАЗАД."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=category['title'], callback_data=f"menu_category_{index}")
        for index, category in enumerate(MENU_DATA)
    ]
    keyboard.add(*buttons)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к выбору меню", callback_data="main_menu_choice"))
    return keyboard

def get_nastoiki_items_keyboard():
    """Возвращает клавиатуру с кнопкой 'назад' для меню настоек."""
    keyboard = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu_nastoiki_main")
    keyboard.add(back_button)
    return keyboard

def get_food_categories_keyboard():
    """Возвращает клавиатуру с категориями кухни И КНОПКОЙ НАЗАД."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=category, callback_data=f"food_category_{category}")
        for category in FOOD_MENU_DATA.keys()
    ]
    keyboard.add(*buttons)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к выбору меню", callback_data="main_menu_choice"))
    return keyboard

def get_food_items_keyboard():
    """Возвращает клавиатуру с кнопкой 'назад' для меню кухни."""
    keyboard = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям кухни", callback_data="menu_food_main")
    keyboard.add(back_button)
    return keyboard

# === INLINE-КЛАВИАТУРЫ ДЛЯ БРОНИРОВАНИЯ ===

def get_booking_options_keyboard():
    """Возвращает клавиатуру с вариантами бронирования."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 Позвонить", callback_data="booking_phone"),
        types.InlineKeyboardButton("🌐 Забронировать через сайт", callback_data="booking_site"),
        types.InlineKeyboardButton("🔐 Написать в секретный чат", callback_data="booking_secret"),
        types.InlineKeyboardButton("🤖 Забронировать через меня", callback_data="booking_bot")
    )
    return markup

def get_booking_confirmation_keyboard():
    """Клавиатура для подтверждения или отмены брони."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✅ Всё верно!", callback_data="confirm_booking"),
        types.InlineKeyboardButton("❌ Начать заново", callback_data="cancel_booking")
    )
    return markup

def get_secret_chat_keyboard():
    """Клавиатура со ссылкой на секретный чат."""
    keyboard = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(text="👉 Перейти в секретный чат", url="https://t.me/stolik_evgenicha")
    keyboard.add(url_button)
    return keyboard

# === INLINE-КЛАВИАТУРЫ ДЛЯ АДМИН-ПАНЕЛИ ===

def get_boss_main_keyboard(settings: dict):
    """
    Главное меню для БОССА. Динамически показывает статус акций.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    group_bonus_promo = settings['promotions']['group_bonus']
    group_bonus_status = "✅ ВКЛ" if group_bonus_promo.get('is_active') else "❌ ВЫКЛ"
    group_bonus_button = types.InlineKeyboardButton(
        f"Бонус для компании: {group_bonus_status}",
        callback_data="boss_toggle_promotions.group_bonus.is_active"
    )

    happy_hours_promo = settings['promotions']['happy_hours']
    happy_hours_status = "✅ ВКЛ" if happy_hours_promo.get('is_active') else "❌ ВЫКЛ"
    happy_hours_button = types.InlineKeyboardButton(
        f"Счастливые часы: {happy_hours_status}",
        callback_data="boss_toggle_promotions.happy_hours.is_active"
    )

    password_promo = settings['promotions']['password_of_the_day']
    password_status = "✅ ВКЛ" if password_promo.get('is_active') else "❌ ВЫКЛ"
    password_toggle_button = types.InlineKeyboardButton(
        f"Пароль дня: {password_status}",
        callback_data="boss_toggle_promotions.password_of_the_day.is_active"
    )
    password_set_button = types.InlineKeyboardButton(
        "🤫 Установить пароль и бонус",
        callback_data="boss_set_password"
    )

    keyboard.add(group_bonus_button, happy_hours_button, password_toggle_button, password_set_button)
    return keyboard
