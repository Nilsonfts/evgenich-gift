# keyboards.py
from telebot import types
from core.config import ALL_ADMINS, ALL_BOOKING_STAFF, MENU_URL
from modules.menu_nastoiki import MENU_DATA
from modules.food_menu import FOOD_MENU_DATA

# === ОСНОВНЫЕ REPLY-КЛАВИАТУРЫ ===

def get_main_menu_keyboard(user_id):
    """Возвращает главную клавиатуру для основного меню."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_button = types.KeyboardButton("📖 Меню")
    friend_button = types.KeyboardButton("🤝 Привести товарища")
    book_button = types.KeyboardButton("📍 Забронировать стол")
    ai_help_button = types.KeyboardButton("🗣 Спроси у Евгенича")

    keyboard.row(ai_help_button, menu_button)
    keyboard.row(book_button, friend_button)

    # Кнопка "Отправить БРОНЬ" для всех, кто может создавать брони (BOSS + ADMIN + SMM)
    if user_id in ALL_BOOKING_STAFF:
        admin_booking_button = types.KeyboardButton("📨 Отправить БРОНЬ")
        
        # Кнопка админки только для BOSS и ADMIN (не для SMM)
        if user_id in ALL_ADMINS:
            admin_button = types.KeyboardButton("👑 Админка")
            keyboard.row(admin_booking_button, admin_button)
        else:
            # Только кнопка брони для SMM
            keyboard.row(admin_booking_button)

    return keyboard

def get_gift_keyboard():
    """Возвращает клавиатуру для получения подарка."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    gift_button = types.KeyboardButton("🥃 Получить настойку по талону")
    keyboard.add(gift_button)
    return keyboard

def get_contact_request_keyboard():
    """Возвращает клавиатуру для запроса контакта (только обязательная кнопка)."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = types.KeyboardButton("📱 Поделиться контактом", request_contact=True)
    keyboard.add(contact_button)
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
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=category['title'], callback_data=f"menu_category_{index}")
        for index, category in enumerate(MENU_DATA)
    ]
    keyboard.add(*buttons)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к выбору меню", callback_data="main_menu_choice"))
    return keyboard

def get_nastoiki_items_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu_nastoiki_main")
    keyboard.add(back_button)
    return keyboard

def get_food_categories_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=category, callback_data=f"food_category_{category}")
        for category in FOOD_MENU_DATA.keys()
    ]
    keyboard.add(*buttons)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к выбору меню", callback_data="main_menu_choice"))
    return keyboard

def get_food_items_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton(text="⬅️ Назад к категориям кухни", callback_data="menu_food_main")
    keyboard.add(back_button)
    return keyboard

# === INLINE-КЛАВИАТУРЫ ДЛЯ БРОНИРОВАНИЯ ===

def get_concept_choice_keyboard():
    """Возвращает клавиатуру для выбора концепции AI-ассистента."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    concepts = [
        ("ЕВГЕНИЧ", "concept_evgenich")
    ]
    
    buttons = [
        types.InlineKeyboardButton(text=name, callback_data=callback_data)
        for name, callback_data in concepts
    ]
    
    keyboard.add(*buttons)
    return keyboard

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

def get_traffic_source_keyboard():
    """Клавиатура для выбора источника трафика при бронировании (для админов)."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📘 ВКонтакте", callback_data="source_vk"),
        types.InlineKeyboardButton("📸 Instagram", callback_data="source_inst")
    )
    keyboard.add(
        types.InlineKeyboardButton("🤖 Бот в ТГ", callback_data="source_bot_tg"),
        types.InlineKeyboardButton("📢 Забронируй Евгенича", callback_data="source_tg")
    )
    return keyboard

def get_bar_selection_keyboard():
    """Клавиатура для выбора бара при бронировании."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🍷 Невский", callback_data="bar_nevsky"),
        types.InlineKeyboardButton("💎 Рубинштейна", callback_data="bar_rubinstein")
    )
    return keyboard

def get_cancel_booking_keyboard():
    """Клавиатура с кнопкой отмены бронирования."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("❌ Отменить бронь", callback_data="cancel_booking")
    )
    return keyboard

# === НОВАЯ СТРУКТУРА АДМИН-ПАНЕЛИ ===

def get_admin_main_menu():
    """Главное меню админки с разделами."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("⚙️ Управление акциями", callback_data="admin_menu_promotions"),
        types.InlineKeyboardButton("📊 Отчеты и аналитика", callback_data="admin_menu_reports"),
        types.InlineKeyboardButton("📝 Управление контентом", callback_data="admin_menu_content"),
        types.InlineKeyboardButton("� Система рассылок", callback_data="admin_menu_broadcasts"),
        types.InlineKeyboardButton("�👥 Управление персоналом", callback_data="admin_menu_staff"),
        types.InlineKeyboardButton("👤 Управление пользователями", callback_data="admin_menu_users"),
        types.InlineKeyboardButton("💾 Управление данными", callback_data="admin_menu_data")
    )
    return keyboard

def get_admin_promotions_menu(settings: dict):
    """Меню для управления промо-акциями."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    group_bonus_promo = settings['promotions']['group_bonus']
    group_bonus_status = "✅ ВКЛ" if group_bonus_promo.get('is_active') else "❌ ВЫКЛ"
    group_bonus_button = types.InlineKeyboardButton(
        f"Бонус компании: {group_bonus_status}",
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
    
    keyboard.add(group_bonus_button, happy_hours_button, password_toggle_button)
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main_menu"))
    return keyboard

def get_admin_reports_menu():
    """Меню для просмотра отчетов."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📊 Текущая смена (реальное время)", callback_data="admin_report_current_shift"),
        types.InlineKeyboardButton("📊 Завершенная смена", callback_data="admin_report_manual_daily"),
        types.InlineKeyboardButton("� Полный отчет за все время", callback_data="admin_report_full_statistics"),
        types.InlineKeyboardButton("�👷 Статистика сотрудников", callback_data="admin_report_staff_realtime"),
        types.InlineKeyboardButton("🔍 Диагностика QR-кодов", callback_data="admin_staff_qr_diagnostics"),
        types.InlineKeyboardButton("🏆 Ударники труда", callback_data="admin_report_leaderboard"),
        types.InlineKeyboardButton("💔 Анализ оттока", callback_data="admin_churn_analysis"),
        types.InlineKeyboardButton("🔬 Воронка по источникам", callback_data="admin_report_source_funnel"),
        types.InlineKeyboardButton("📈 Анализ оттока по источникам", callback_data="admin_report_churn_by_source"),
        types.InlineKeyboardButton("🕒 Пики активности гостей", callback_data="admin_report_activity_time")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main_menu"))
    return keyboard

def get_admin_content_menu():
    """Меню для управления контентом."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📧 Система рассылок", callback_data="admin_newsletter_main"),
        types.InlineKeyboardButton("🤫 Установить пароль", callback_data="boss_set_password"),
        types.InlineKeyboardButton("🎤 Загрузить аудио", callback_data="boss_upload_audio")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main_menu"))
    return keyboard

def get_admin_users_menu():
    """Меню для управления пользователями."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_find_user"),
        types.InlineKeyboardButton("🎁 Выдать купон вручную", callback_data="admin_issue_coupon_manual")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main_menu"))
    return keyboard
    
def get_admin_data_menu():
    """Меню для управления данными."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📥 Выгрузить в Google Sheets", callback_data="admin_export_sheets")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main_menu"))
    return keyboard

def get_admin_staff_menu():
    """Меню для управления персоналом."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📋 Список сотрудников", callback_data="admin_list_staff")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main_menu"))
    return keyboard

def get_staff_management_keyboard(staff_id: int, current_status: str):
    """Клавиатура для управления конкретным сотрудником."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    new_status = 'inactive' if current_status == 'active' else 'active'
    button_text = "❌ Деактивировать" if current_status == 'active' else "✅ Активировать"
    
    keyboard.add(
        types.InlineKeyboardButton(button_text, callback_data=f"admin_toggle_staff_{staff_id}_{new_status}")
    )
    return keyboard

def get_position_choice_keyboard():
    """Клавиатура для выбора должности при регистрации сотрудника."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🤵 Официант", callback_data="staff_reg_pos_Официант"),
        types.InlineKeyboardButton("🍸 Бармен", callback_data="staff_reg_pos_Бармен"),
        types.InlineKeyboardButton("🎩 Менеджер", callback_data="staff_reg_pos_Менеджер")
    )
    return keyboard

# === КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ РАССЫЛОК ===

def get_content_management_menu():
    """Главное меню управления контентом."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📊 Статистика базы", callback_data="admin_content_stats"),
        types.InlineKeyboardButton("✉️ Создать рассылку", callback_data="admin_content_create")
    )
    keyboard.add(
        types.InlineKeyboardButton("📋 Мои рассылки", callback_data="admin_content_list"),
        types.InlineKeyboardButton("📈 Аналитика рассылок", callback_data="admin_content_analytics")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
    )
    return keyboard

def get_newsletter_creation_choice_menu():
    """Меню выбора способа создания рассылки."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🎯 Использовать шаблон", callback_data="admin_newsletter_template_choice"),
        types.InlineKeyboardButton("✏️ Создать свой", callback_data="admin_newsletter_custom_choice")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_newsletter_main")
    )
    return keyboard

def get_newsletter_template_categories():
    """Меню выбора категории шаблона."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("� Акции и скидки", callback_data="admin_template_promo"),
        types.InlineKeyboardButton("🍽 Новое меню", callback_data="admin_template_menu")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎵 Мероприятия", callback_data="admin_template_event"),
        types.InlineKeyboardButton("📅 Бронирование", callback_data="admin_template_booking")
    )
    keyboard.add(
        types.InlineKeyboardButton("👋 Приветствие", callback_data="admin_template_welcome"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_content_create")
    )
    return keyboard

def get_newsletter_sending_menu(newsletter_id: int):
    """Меню отправки рассылки."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📧 Тестовая отправка", callback_data=f"admin_newsletter_test_{newsletter_id}"),
        types.InlineKeyboardButton("🚀 Отправить сейчас", callback_data=f"admin_newsletter_send_{newsletter_id}"),
        types.InlineKeyboardButton("⏰ Запланировать", callback_data=f"admin_newsletter_schedule_{newsletter_id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_menu_content")
    )
    return keyboard

def get_newsletter_buttons_menu(newsletter_id: int):
    """Меню управления кнопками рассылки."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("➕ Добавить кнопку", callback_data=f"admin_newsletter_add_button_{newsletter_id}"),
        types.InlineKeyboardButton("✅ Готово", callback_data=f"admin_newsletter_ready_{newsletter_id}")
    )
    return keyboard

def get_button_templates_menu(newsletter_id: int):
    """Шаблоны кнопок для рассылки."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📍 Забронировать стол", callback_data=f"admin_button_template_{newsletter_id}_booking"),
        types.InlineKeyboardButton("🌐 Перейти на сайт", callback_data=f"admin_button_template_{newsletter_id}_website"),
        types.InlineKeyboardButton("📖 Меню", callback_data=f"admin_button_template_{newsletter_id}_menu"),
        types.InlineKeyboardButton("🎯 Своя кнопка", callback_data=f"admin_button_template_{newsletter_id}_custom")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data=f"admin_newsletter_buttons_{newsletter_id}")
    )
    return keyboard

def get_newsletter_list_keyboard(newsletters):
    """Клавиатура со списком рассылок."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for newsletter in newsletters:
        status_emoji = {
            'draft': '📝',
            'scheduled': '⏰', 
            'sent': '✅',
            'sending': '📤'
        }.get(newsletter['status'], '❓')
        
        button_text = f"{status_emoji} {newsletter['title'][:30]}..."
        keyboard.add(
            types.InlineKeyboardButton(button_text, callback_data=f"admin_newsletter_view_{newsletter['id']}")
        )
    
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_menu_content")
    )
    return keyboard

def get_newsletter_view_keyboard(newsletter_id: int, status: str):
    """Клавиатура просмотра конкретной рассылки."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    if status == 'draft':
        keyboard.add(
            types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"admin_newsletter_edit_{newsletter_id}"),
            types.InlineKeyboardButton("🚀 Отправить", callback_data=f"admin_newsletter_send_menu_{newsletter_id}")
        )
    
    keyboard.add(
        types.InlineKeyboardButton("📊 Аналитика", callback_data=f"admin_newsletter_stats_{newsletter_id}"),
        types.InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_newsletter_delete_{newsletter_id}")
    )
    
    keyboard.add(
        types.InlineKeyboardButton("🔙 К списку", callback_data="admin_content_list")
    )
    return keyboard

def create_newsletter_inline_keyboard(buttons_data):
    """Создает inline-клавиатуру для рассылки из данных кнопок."""
    if not buttons_data:
        return None
        
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for button in buttons_data:
        keyboard.add(
            types.InlineKeyboardButton(button['text'], url=button['url'])
        )
    return keyboard

def get_newsletter_creation_choice_menu():
    """Меню выбора способа создания рассылки."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🎯 Использовать шаблон", callback_data="admin_newsletter_template_choice"),
        types.InlineKeyboardButton("✏️ Создать свой", callback_data="admin_newsletter_custom_choice")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_newsletter_main")
    )
    return keyboard

def get_newsletter_template_categories():
    """Меню выбора категории шаблона."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎉 Акции и скидки", callback_data="admin_template_promo"),
        types.InlineKeyboardButton("🍽 Новое меню", callback_data="admin_template_menu")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎵 Мероприятия", callback_data="admin_template_event"),
        types.InlineKeyboardButton("📅 Бронирование", callback_data="admin_template_booking")
    )
    keyboard.add(
        types.InlineKeyboardButton("👋 Приветствие", callback_data="admin_template_welcome"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_content_create")
    )
    return keyboard

def get_newsletter_creation_menu():
    """Меню создания рассылки (оригинальное)."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📝 Текстовая рассылка", callback_data="admin_newsletter_type_text"),
        types.InlineKeyboardButton("🖼 Рассылка с картинкой", callback_data="admin_newsletter_type_photo"),
        types.InlineKeyboardButton("🎥 Рассылка с видео", callback_data="admin_newsletter_type_video")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_content_create")
    )
    return keyboard

def get_admin_broadcasts_menu():
    """Меню системы рассылок."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📝 Создать рассылку", callback_data="broadcast_create"),
        types.InlineKeyboardButton("📊 Статистика рассылок", callback_data="broadcast_stats"),
        types.InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_menu_main")
    )
    return keyboard

def get_template_preview_keyboard(category: str):
    """Клавиатура для предпросмотра шаблона."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("✅ Использовать этот шаблон", callback_data=f"admin_use_template_{category}"),
        types.InlineKeyboardButton("✏️ Редактировать шаблон", callback_data=f"admin_edit_template_{category}"),
        types.InlineKeyboardButton("🔙 Выбрать другой", callback_data="admin_newsletter_template_choice")
    )
    return keyboard
