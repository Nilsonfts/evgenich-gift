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
        # ИЗМЕНЕНО: Добавлен эмодзи
        admin_button = types.KeyboardButton("👑 админка")
        keyboard.row(admin_button)
        
    return keyboard

# ... (остальные Reply-клавиатуры без изменений) ...

# === INLINE-КЛАВИАТУРЫ ДЛЯ МЕНЮ (С ИСПРАВЛЕНИЕМ КНОПКИ "НАЗАД") ===

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
    # ИСПРАВЛЕНО: Добавлена кнопка "Назад"
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к выбору меню", callback_data="main_menu_choice"))
    return keyboard

def get_food_categories_keyboard():
    """Возвращает клавиатуру с категориями кухни И КНОПКОЙ НАЗАД."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=category, callback_data=f"food_category_{category}")
        for category in FOOD_MENU_DATA.keys()
    ]
    keyboard.add(*buttons)
    # ИСПРАВЛЕНО: Добавлена кнопка "Назад"
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к выбору меню", callback_data="main_menu_choice"))
    return keyboard

# ... (все остальные клавиатуры без изменений, я их привожу для полноты) ...

def get_nastoiki_items_keyboard():
    """Возвращает клавиатуру с кнопкой 'назад' для меню настоек."""
    keyboard = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu_nastoiki_main")
    keyboard.add(back_button)
    return keyboard

def get_food_items_keyboard():
    """Возвращает клавиатуру с кнопкой 'назад' для меню кухни."""
    keyboard = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям кухни", callback_data="menu_food_main")
    keyboard.add(back_button)
    return keyboard

# ... (booking keyboards) ...
def get_booking_options_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 Позвонить", callback_data="booking_phone"),
        types.InlineKeyboardButton("🌐 Забронировать через сайт", callback_data="booking_site"),
        types.InlineKeyboardButton("🔐 Написать в секретный чат", callback_data="booking_secret"),
        types.InlineKeyboardButton("🤖 Забронировать через меня", callback_data="booking_bot")
    )
    return markup

def get_booking_confirmation_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✅ Всё верно!", callback_data="confirm_booking"),
        types.InlineKeyboardButton("❌ Начать заново", callback_data="cancel_booking")
    )
    return markup

def get_secret_chat_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(text="👉 Перейти в секретный чат", url="https://t.me/stolik_evgenicha")
    keyboard.add(url_button)
    return keyboard

# === АДМИН-ПАНЕЛЬ ===
def get_boss_main_keyboard(settings: dict):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    group_bonus_promo = settings['promotions']['group_bonus']
    group_bonus_status = "✅ ВКЛ" if group_bonus_promo['is_active'] else "❌ ВЫКЛ"
    group_bonus_button = types.InlineKeyboardButton(
        f"Бонус для компании: {group_bonus_status}",
        callback_data="boss_toggle_promotions.group_bonus.is_active"
    )
    happy_hours_promo = settings['promotions']['happy_hours']
    happy_hours_status = "✅ ВКЛ" if happy_hours_promo['is_active'] else "❌ ВЫКЛ"
    happy_hours_button = types.InlineKeyboardButton(
        f"Счастливые часы: {happy_hours_status}",
        callback_data="boss_toggle_promotions.happy_hours.is_active"
    )
    password_promo = settings['promotions']['password_of_the_day']
    password_status = "✅ ВКЛ" if password_promo['is_active'] else "❌ ВЫКЛ"
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
