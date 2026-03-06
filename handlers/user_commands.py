# /handlers/user_commands.py

import logging
import datetime
from telebot import types

from core.config import CHANNEL_ID, CHANNEL_ID_MSK, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, ALL_ADMINS, REPORT_CHAT_ID, NASTOYKA_NOTIFICATIONS_CHAT_ID, BOOKING_NOTIFICATIONS_CHAT_ID, get_channel_id_for_user
import core.database as database
import core.settings_manager as settings_manager
import texts
import keyboards
from utils.qr_generator import create_qr_code

# Словарь для хранения текущего payload пользователя (для определения канала)
user_current_payload = {}

# --- Вспомогательные функции ---

def get_channel_for_payload(payload: str) -> str:
    """Определяет канал напрямую по payload (жёсткая привязка)."""
    # Общая проверка для всех _msk источников
    if payload and payload.endswith('_msk'):
        logging.info(f"🎯 Payload '{payload}' -> Московский канал @evgenichmoscow")
        return CHANNEL_ID_MSK
    logging.info(f"🎯 Payload '{payload}' -> Питерский канал {CHANNEL_ID}")
    return CHANNEL_ID

def issue_coupon(bot, user_id, chat_id):
    """Выдает пользователю купон на настойку."""
    database.update_status(user_id, 'issued')

    try:
        bot.send_sticker(chat_id, NASTOYKA_STICKER_ID)
    except Exception as e:
        logging.error(f"Не удалось отправить стикер-купон: {e}")

    bot.send_message(
        chat_id,
        texts.COUPON_TEXT,
        parse_mode="Markdown",
        reply_markup=keyboards.get_redeem_keyboard()
    )

# --- Основные обработчики команд ---

def register_user_command_handlers(bot):
    """Регистрирует обработчики для основных команд пользователя и персонала."""
    
    # Словарь для хранения состояний регистрации персонала (имя, должность)
    staff_reg_data = {} 
    
    # Словарь для хранения состояний сбора данных профиля пользователя
    user_profile_data = {} 

    @bot.message_handler(commands=['concept'])
    def handle_concept_choice(message: types.Message):
        """Показывает меню выбора концепции для AI-ассистента."""
        user_id = message.from_user.id
        
        current_concept = database.get_user_concept(user_id)
        concept_names = {
            "evgenich": "ЕВГЕНИЧ (Классический)"
        }
        
        current_name = concept_names.get(current_concept, "ЕВГЕНИЧ (Классический)")
        
        bot.send_message(
            message.chat.id,
            f"🎭 **Настройка AI-ассистента**\n\n"
            f"Доступная концепция для этого чата:\n\n"
            f"Текущая концепция: **{current_name}**",
            reply_markup=keyboards.get_concept_choice_keyboard(),
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """
        Обрабатывает команду /start, регистрирует нового пользователя или показывает главное меню.
        Работает ТОЛЬКО в личных сообщениях!
        """
        try:
            # Проверяем тип чата - регистрация только в личке!
            if message.chat.type != 'private':
                logging.info(f"Попытка /start в групповом чате {message.chat.id}. Отклоняем.")
                bot.reply_to(
                    message, 
                    "🔒 Регистрация и получение бесплатной настойки доступны только в личных сообщениях!\n\n"
                    "Напиши мне в личку: @evgenichspbbot 🥃"
                )
                return
            
            user_id = message.from_user.id
            status = database.get_reward_status(user_id)
            
            # Сохраняем payload для определения канала (ЖЁСТКАЯ ПРИВЯЗКА)
            args = message.text.split(' ', 1)
            if len(args) > 1:
                current_payload = args[1]
                user_current_payload[user_id] = current_payload
                logging.info(f"🎯 СОХРАНЁН PAYLOAD для {user_id}: '{current_payload}'")
            
            # Детальное логирование для отладки
            logging.info(f"🔍 /start от {user_id}: message.text='{message.text}', status='{status}', payload={user_current_payload.get(user_id, 'нет')}")

            # Проверяем, есть ли параметр booking (для любых пользователей)
            if len(args) > 1 and args[1] == 'booking':
                logging.info(f"✅ Пользователь {user_id} запускает быстрое бронирование через deep link")
                try:
                    from tinydb import TinyDB, Query
                    
                    # Инициализируем базу бронирований
                    db = TinyDB('booking_data.json')
                    User = Query()
                    
                    # Сразу начинаем процесс бронирования
                    db.upsert({'user_id': user_id, 'step': 'name', 'data': {'is_guest_booking': True}}, User.user_id == user_id)
                    bot.send_message(
                        message.chat.id, 
                        "🌟 Отлично! Давайте забронируем столик.\n\n"
                        "Как вас зовут?",
                        reply_markup=keyboards.get_cancel_booking_keyboard()
                    )
                    return
                except Exception as e:
                    logging.error(f"Ошибка запуска быстрого бронирования: {e}")
                    bot.send_message(
                        user_id, 
                        "Что-то пошло не так 😅\n\nПопробуйте через кнопку в меню или позвоните: +7 (812) 237-59-50"
                    )
                    return

            if status in ['redeemed', 'redeemed_and_left']:
                # Проверяем, пришел ли пользователь по новой ссылке - обновляем source
                args = message.text.split(' ', 1)
                if len(args) > 1:
                    payload = args[1]
                    allowed_sources = {
                        'qr_tv': 'QR-код на ТВ СПБ', 
                        'qr_bar': 'QR-код на баре СПБ', 
                        'qr_waiter': 'QR от официанта СПБ',
                        'qr_stol': 'QR-код на столе СПБ',
                        'vk': 'Ссылка из ВКонтакте СПБ', 
                        'inst': 'Ссылка из Instagram СПБ', 
                        'menu': 'Меню в баре СПБ',
                        'flyer': 'Листовка на улице СПБ', 
                        'street': 'Уличное Меню СПБ',
                        '2gis': '2ГИС Кнопка СПБ',
                        'site': 'Кнопка Сайт СПБ',
                        'taplink': 'Таплинк на ТВ СПБ',
                        'rubik_street_offline': 'ЕВГ РУБ около бара СПБ',
                        'qr_rubik_steer_offline': 'QR Рубик около бара СПБ',
                        # Московские метки
                        'qr_tv_msk': 'QR-код на ТВ МСК',
                        'qr_bar_msk': 'QR-код на баре МСК',
                        'qr_waiter_msk': 'QR от официанта МСК',
                        'qr_stol_msk': 'QR-код на столе МСК',
                        'vk_msk': 'Ссылка из ВКонтакте МСК',
                        'inst_msk': 'Ссылка из Instagram МСК',
                        'menu_msk': 'Меню в баре МСК',
                        'flyer_msk': 'Листовка на улице МСК',
                        'street_msk': 'Уличное Меню МСК',
                        '2gis_msk': '2ГИС Кнопка МСК',
                        'site_msk': 'Кнопка Сайт МСК'
                    }
                    if payload in allowed_sources:
                        new_source = allowed_sources[payload]
                        database.update_user_source(user_id, new_source)
                        logging.info(f"Обновлен source для существующего пользователя {user_id}: {new_source}")
                
                logging.info(f"Пользователь {user_id} уже получал награду. Показываем основное меню.")
                bot.send_message(
                    user_id,
                    texts.ALREADY_REDEEMED_TEXT,
                    reply_markup=keyboards.get_main_menu_keyboard(user_id),
                    parse_mode="Markdown"
                )
                return

            if status == 'not_found':
                logging.info(f"Новый пользователь {user_id}. Регистрируем в SQLite...")
                referrer_id = None
                brought_by_staff_id = None
                source = 'direct'
                
                args = message.text.split(' ', 1)
                if len(args) > 1:
                    payload = args[1]
                    logging.info(f"Пользователь {user_id} (@{message.from_user.username}) использует payload: {payload}")

                    if payload.startswith('w_'):
                        staff_code = payload.replace('w_', '')
                        logging.info(f"🔍 Попытка привязки к сотруднику с кодом: {staff_code} (пользователь: {user_id})")
                        staff_member = database.find_staff_by_code(staff_code)
                        if staff_member:
                            brought_by_staff_id = staff_member['staff_id']
                            source = "staff"
                            logging.info(f"✅ Пользователь {user_id} (@{message.from_user.username}) успешно привязан к сотруднику: {staff_member['full_name']} (ID: {staff_member['staff_id']}, код: {staff_code})")
                            # Отправляем уведомление администраторам о новом переходе по QR-коду сотрудника
                            bot.send_message(
                                NASTOYKA_NOTIFICATIONS_CHAT_ID,
                                f"📊 QR-переход: Новый гость привлечен сотрудником {staff_member['short_name']} "
                                f"(@{message.from_user.username or 'без_username'})",
                                parse_mode="Markdown"
                            )
                        else:
                            logging.warning(f"❌ QR-код сотрудника некорректен! Код '{staff_code}' не найден в базе активных сотрудников. Переход засчитан как 'direct'.")
                            # При неправильном коде сотрудника считаем переход "прямым"
                            source = 'direct'
                            brought_by_staff_id = None
                    elif payload == 'booking':
                        # Пользователь пришел для бронирования - сразу запускаем форму ввода
                        logging.info(f"Пользователь {user_id} пришел для бронирования через групповую кнопку")
                        # Если пользователь новый, быстро регистрируем его
                        if status == 'not_found':
                            source = 'Группа бронирования'
                            database.add_new_user(user_id, message.from_user.username, message.from_user.first_name, source, None, None)
                        
                        # Импортируем TinyDB и сразу запускаем процесс бронирования
                        try:
                            from tinydb import TinyDB, Query
                            
                            # Инициализируем базу бронирований (та же что в booking_flow.py)
                            db = TinyDB('booking_data.json')
                            User = Query()
                            
                            # Сразу начинаем процесс бронирования (как booking_bot callback)
                            db.upsert({'user_id': user_id, 'step': 'name', 'data': {'is_guest_booking': True}}, User.user_id == user_id)
                            bot.send_message(
                                message.chat.id, 
                                "🌟 Отлично! Давайте забронируем для вас столик.\n\n"
                                "Как вас зовут?",
                                reply_markup=keyboards.get_cancel_booking_keyboard()
                            )
                            return
                        except Exception as e:
                            logging.error(f"Ошибка запуска бронирования: {e}")
                            bot.send_message(user_id, "❌ Ошибка при запуске бронирования. Используйте команду /book")
                            return
                    elif payload.startswith('ref_'):
                        try:
                            referrer_id = int(payload.replace('ref_', ''))
                            source = 'Реферал'
                            logging.info(f"Пользователь {user_id} приглашен рефералом {referrer_id}")
                        except (ValueError, IndexError):
                            logging.warning(f"Не удалось распознать ref_id из {payload}")
                    else:
                        allowed_sources = {
                            'qr_tv': 'QR-код на ТВ СПБ', 
                            'qr_bar': 'QR-код на баре СПБ', 
                            'qr_waiter': 'QR от официанта СПБ',
                            'qr_stol': 'QR-код на столе СПБ',
                            'vk': 'Ссылка из ВКонтакте СПБ', 
                            'inst': 'Ссылка из Instagram СПБ', 
                            'menu': 'Меню в баре СПБ',
                            'flyer': 'Листовка на улице СПБ', 
                            'street': 'Уличное Меню СПБ',
                            '2gis': '2ГИС Кнопка СПБ',
                            'site': 'Кнопка Сайт СПБ',
                            'taplink': 'Таплинк на ТВ СПБ',
                            'rubik_street_offline': 'ЕВГ РУБ около бара СПБ',
                            'qr_rubik_steer_offline': 'QR Рубик около бара СПБ',
                            # Московские метки
                            'qr_tv_msk': 'QR-код на ТВ МСК',
                            'qr_bar_msk': 'QR-код на баре МСК',
                            'qr_waiter_msk': 'QR от официанта МСК',
                            'qr_stol_msk': 'QR-код на столе МСК',
                            'vk_msk': 'Ссылка из ВКонтакте МСК',
                            'inst_msk': 'Ссылка из Instagram МСК',
                            'menu_msk': 'Меню в баре МСК',
                            'flyer_msk': 'Листовка на улице МСК',
                            'street_msk': 'Уличное Меню МСК',
                            '2gis_msk': '2ГИС Кнопка МСК',
                            'site_msk': 'Кнопка Сайт МСК'
                        }
                        if payload in allowed_sources:
                            source = allowed_sources[payload]
                            logging.info(f"Пользователь {user_id} пришел из источника: {source}")
                        else:
                            logging.warning(f"Неизвестный источник: {payload}. Устанавливаем как direct.")

                logging.info(f"Регистрация пользователя {user_id}: источник='{source}', сотрудник_id={brought_by_staff_id}, реферер={referrer_id}")
                database.add_new_user(user_id, message.from_user.username, message.from_user.first_name, source, referrer_id, brought_by_staff_id)
                if referrer_id:
                    bot.send_message(user_id, texts.NEW_USER_REFERRED_TEXT)
            else:
                # Существующий пользователь (issued, registered) - обновляем source если пришел по новой ссылке
                args = message.text.split(' ', 1)
                logging.info(f"🔍 Существующий пользователь {user_id}, проверяю payload: args={args}")
                if len(args) > 1:
                    payload = args[1]
                    logging.info(f"🔍 Payload для {user_id}: '{payload}'")
                    allowed_sources = {
                        'qr_tv': 'QR-код на ТВ СПБ', 
                        'qr_bar': 'QR-код на баре СПБ', 
                        'qr_waiter': 'QR от официанта СПБ',
                        'qr_stol': 'QR-код на столе СПБ',
                        'vk': 'Ссылка из ВКонтакте СПБ', 
                        'inst': 'Ссылка из Instagram СПБ', 
                        'menu': 'Меню в баре СПБ',
                        'flyer': 'Листовка на улице СПБ', 
                        'street': 'Уличное Меню СПБ',
                        '2gis': '2ГИС Кнопка СПБ',
                        'site': 'Кнопка Сайт СПБ',
                        'taplink': 'Таплинк на ТВ СПБ',
                        'rubik_street_offline': 'ЕВГ РУБ около бара СПБ',
                        'qr_rubik_steer_offline': 'QR Рубик около бара СПБ',
                        # Московские метки
                        'qr_tv_msk': 'QR-код на ТВ МСК',
                        'qr_bar_msk': 'QR-код на баре МСК',
                        'qr_waiter_msk': 'QR от официанта МСК',
                        'qr_stol_msk': 'QR-код на столе МСК',
                        'vk_msk': 'Ссылка из ВКонтакте МСК',
                        'inst_msk': 'Ссылка из Instagram МСК',
                        'menu_msk': 'Меню в баре МСК',
                        'flyer_msk': 'Листовка на улице МСК',
                        'street_msk': 'Уличное Меню МСК',
                        '2gis_msk': '2ГИС Кнопка МСК',
                        'site_msk': 'Кнопка Сайт МСК'
                    }
                    if payload in allowed_sources:
                        new_source = allowed_sources[payload]
                        logging.info(f"✅ Обновляю source для {user_id}: '{new_source}'")
                        database.update_user_source(user_id, new_source)
                        logging.info(f"✅ Source обновлен для пользователя {user_id}: {new_source}")
                    else:
                        logging.warning(f"⚠️ Payload '{payload}' не найден в allowed_sources!")

            # Отправляем приветствие с кнопкой получения подарка
            bot.send_message(
                message.chat.id,
                texts.WELCOME_TEXT,
                reply_markup=keyboards.get_gift_keyboard()
            )
        
        except Exception as e:
            logging.error(f"❌ Ошибка в handle_start для пользователя {message.from_user.id}: {e}")
            logging.error(f"Тип ошибки: {type(e).__name__}")
            try:
                bot.send_message(
                    message.from_user.id,
                    "❌ Произошла ошибка при обработке команды. Попробуйте ещё раз через /start"
                )
            except Exception:
                pass  # Если даже отправка сообщения об ошибке не работает

    # --- ИСПРАВЛЕННАЯ ЛОГИКА РЕГИСТРАЦИИ ПЕРСОНАЛА ---

    def process_staff_name_step(message: types.Message):
        """Шаг 2: Обработка введенного имени сотрудника."""
        user_id = message.from_user.id
        
        # Проверяем, что мы действительно ждем имя от этого пользователя
        if staff_reg_data.get(user_id) != 'awaiting_name':
            # Если нет, передаем управление дальше (например, AI)
            return

        full_name = message.text.strip()
        if len(full_name.split()) < 2:
            bot.send_message(user_id, "Пожалуйста, введите и имя, и фамилию. Например: Иван Смирнов")
            # Снова регистрируем этот же шаг, чтобы бот ждал правильного ввода
            bot.register_next_step_handler(message, process_staff_name_step)
            return
        
        # Сохраняем имя и переводим на следующий шаг
        staff_reg_data[user_id] = {'full_name': full_name}
        bot.send_message(user_id, f"Отлично, {full_name.split()[0]}! Теперь выбери свою должность:",
                         reply_markup=keyboards.get_position_choice_keyboard())

    @bot.callback_query_handler(func=lambda call: call.data.startswith("staff_reg_pos_"))
    def handle_staff_position_choice(call: types.CallbackQuery):
        """Шаг 3: Обработка выбора должности."""
        user_id = call.from_user.id
        user_state = staff_reg_data.get(user_id)
        
        if not isinstance(user_state, dict) or 'full_name' not in user_state:
            bot.answer_callback_query(call.id, "Что-то пошло не так. Попробуйте начать регистрацию заново с команды /staff_reg", show_alert=True)
            return
            
        position = call.data.replace("staff_reg_pos_", "")
        full_name = user_state['full_name']
        
        bot.answer_callback_query(call.id, text=f"Должность: {position}")
        bot.edit_message_text("Отлично, регистрирую тебя в системе...", call.message.chat.id, call.message.message_id)
        
        unique_code = database.add_or_update_staff(user_id, full_name, position)
        
        if unique_code:
            bot.send_message(user_id, "Супер! Ты в системе.", reply_markup=keyboards.get_main_menu_keyboard(user_id))
            send_qr_to_staff(bot, user_id, unique_code)
        else:
            bot.send_message(user_id, "Произошла ошибка при регистрации. Обратись к администратору.", reply_markup=keyboards.get_main_menu_keyboard(user_id))
            
        if user_id in staff_reg_data:
            del staff_reg_data[user_id]


    @bot.message_handler(commands=['staff_reg'])
    def handle_staff_reg(message: types.Message):
        """Шаг 1: Инициация регистрации персонала."""
        user_id = message.from_user.id
        
        if message.chat.type == 'private':
            bot.send_message(user_id, "Эту команду нужно использовать в рабочем чате, чтобы я понял, что ты из команды.")
            return

        try:
            member = bot.get_chat_member(REPORT_CHAT_ID, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return # Игнорируем, если не состоит в чате
        except Exception as e:
            logging.warning(f"Не удалось проверить членство {user_id} в рабочем чате: {e}")
            return
        
        existing_staff = database.find_staff_by_telegram_id(user_id)
        if existing_staff:
             msg_to_send = bot.send_message(user_id, "Ты уже зарегистрирован в системе. Чтобы получить свой QR-код, используй команду /myqr")
             return

        # Начинаем регистрацию в личных сообщениях
        msg = bot.send_message(user_id, "Привет! Вижу, ты из нашей команды. Давай зарегистрируем тебя в системе.\n\n"
                                  "**Пожалуйста, введи свои полные Имя и Фамилию** (например, 'Иван Смирнов'). "
                                  "Эти данные будет видеть руководство в отчетах по эффективности.", parse_mode="Markdown")
        
        # "Запираем" бота в ожидании следующего шага от этого пользователя
        staff_reg_data[user_id] = 'awaiting_name'
        bot.register_next_step_handler(msg, process_staff_name_step)

    def send_qr_to_staff(bot, user_id, unique_code):
        bot_info = bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start=w_{unique_code}"
        
        qr_image = create_qr_code(link)
        
        bot.send_photo(user_id, qr_image, caption="Вот твой персональный QR-код для привлечения гостей. "
                                                  "Показывай его прямо с экрана телефона.\n\n"
                                                  "Ты всегда можешь получить его снова командой /myqr")

    @bot.message_handler(commands=['myqr'])
    def handle_my_qr(message: types.Message):
        user_id = message.from_user.id
        staff_member = database.find_staff_by_telegram_id(user_id)
        
        if staff_member and staff_member['status'] == 'active':
            send_qr_to_staff(bot, user_id, staff_member['unique_code'])
        else:
            bot.send_message(user_id, "Я не нашел тебя в активной базе персонала. Если ты новый сотрудник, используй команду /staff_reg в рабочем чате.")


    # --- Система отзывов ---

    # Состояния ожидания текста отзыва
    review_states = {}

    @bot.message_handler(commands=['review'])
    @bot.message_handler(func=lambda message: message.text == "⭐ Оставить отзыв")
    def handle_review_command(message: types.Message):
        """Показывает inline-клавиатуру с выбором звёзд 1-5."""
        if message.chat.type != 'private':
            bot.reply_to(message, "⭐ Отзыв можно оставить только в личных сообщениях!")
            return

        text = (
            "⭐ *Оцените наш бар!*\n\n"
            "Ваше мнение очень важно для нас ❤️\n"
            "Выберите оценку от 1 до 5:"
        )
        keyboard = types.InlineKeyboardMarkup(row_width=5)
        keyboard.add(
            *[types.InlineKeyboardButton(
                "⭐" * i, callback_data=f"review_star_{i}"
            ) for i in range(1, 6)]
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('review_star_'))
    def handle_review_star(call: types.CallbackQuery):
        """Обрабатывает выбор звёзд в отзыве."""
        user_id = call.from_user.id
        rating = int(call.data.split('_')[2])
        bot.answer_callback_query(call.id)

        logging.info(f"⭐ Пользователь {user_id} (@{call.from_user.username}) оценил: {rating} звёзд")

        if rating >= 4:
            # Позитив → ссылки на площадки
            bot.edit_message_text(
                f"{'⭐' * rating}\n\n"
                "Нам очень приятно! 🥰\n"
                "Будем благодарны, если оставите отзыв на одной из площадок:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_get_review_links_keyboard()
            )
        else:
            # Негатив → просим написать текст
            bot.edit_message_text(
                f"{'⭐' * rating}\n\n"
                "Мы крайне раздосадованы 😔\n"
                "Расскажите, что нам исправить?\n\n"
                "_Напишите ваш отзыв следующим сообщением:_",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=None
            )
            review_states[user_id] = rating
            bot.register_next_step_handler(call.message, _process_negative_review, rating)

    def _process_negative_review(message: types.Message, rating: int):
        """Получает текст негативного отзыва и отправляет в чат лидов."""
        user_id = message.from_user.id
        review_states.pop(user_id, None)

        if not message.text:
            bot.send_message(message.chat.id, "Отзыв не получен. Попробуйте ещё раз через /review")
            return

        review_text = message.text
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        username = message.from_user.username

        # Формируем уведомление для чата лидов
        lead_msg = (
            f"📝 <b>НОВЫЙ ОТЗЫВ</b> — {'⭐' * rating}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 {first_name} {last_name}\n"
        )
        if username:
            lead_msg += f"📱 @{username}\n"
        lead_msg += (
            f"🆔 <code>{user_id}</code>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💬 {review_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        # Отправляем в чат лидов
        sent = False
        if REPORT_CHAT_ID:
            try:
                bot.send_message(int(REPORT_CHAT_ID), lead_msg, parse_mode="HTML")
                sent = True
                logging.info(f"📝 Отзыв от {user_id} отправлен в REPORT_CHAT_ID")
            except Exception as e:
                logging.error(f"Ошибка отправки отзыва в REPORT_CHAT_ID: {e}")

        # Дублируем боссам если не ушло в чат
        if not sent:
            from core.config import BOSS_IDS
            for boss_id in BOSS_IDS:
                try:
                    bot.send_message(boss_id, lead_msg, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Не удалось отправить отзыв боссу {boss_id}: {e}")

        # Благодарим пользователя
        bot.send_message(
            message.chat.id,
            "❤️ *Евгенич услышал!*\n\n"
            "Спасибо, что помогаете нам стать лучше.\n"
            "Мы обязательно учтём ваше мнение!",
            parse_mode="Markdown",
            reply_markup=keyboards.get_main_menu_keyboard(user_id)
        )

    def _get_review_links_keyboard():
        """Возвращает inline-клавиатуру со ссылками на площадки отзывов."""
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton(
                "📍 Яндекс Карты",
                url="https://yandex.ru/maps/org/yevgenich/119499600311/reviews/?add-review=true"
            ),
            types.InlineKeyboardButton(
                "📍 2ГИС",
                url="https://2gis.ru/spb/firm/70000001100534789/tab/reviews"
            ),
            types.InlineKeyboardButton(
                "📍 Restoclub",
                url="https://www.restoclub.ru/spb/place/evgenich-1/opinions#newReview"
            ),
            types.InlineKeyboardButton(
                "📍 Google Maps",
                url="https://www.google.com/maps/place//data=!4m3!3m2!1s0x46962162657b16bf:0x40cc9891e0960b0f!12e1?source=g.page.m.nr._&laa=nmx-review-solicitation-recommendation-card"
            ),
            types.InlineKeyboardButton(
                "📍 Zoon",
                url="https://zoon.ru/spb/restaurants/bar_evgenich_na_nevskom_prospekte/reviews/"
            ),
        )
        return kb

    @bot.message_handler(func=lambda message: message.text == "🎁 Карта лояльности")
    def handle_loyalty_card(message: types.Message):
        """Обрабатывает кнопку карты лояльности — показывает баланс GMB + ссылку на регистрацию."""
        if message.chat.type != 'private':
            bot.reply_to(message, "🔒 Карта лояльности доступна только в личных сообщениях! Напиши мне в личку: @evgenichspbbot")
            return

        user_id = message.from_user.id
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        username = message.from_user.username or ""
        full_name = f"{first_name} {last_name}".strip()

        # Получаем телефон из базы данных (если пользователь уже делился контактом)
        phone = database.get_user_phone(user_id) if hasattr(database, 'get_user_phone') else None

        # Логируем запрос карты лояльности
        logging.info(f"🎁 Карта лояльности запрошена: user_id={user_id}, name={full_name}, username=@{username}, phone={phone}")

        # ── Пытаемся получить баланс из GetMeBack ──
        gmb_info = None
        if phone:
            try:
                from utils.gmb_client import gmb
                if gmb.is_configured():
                    gmb_info = gmb.find_client_by_phone(phone)
            except Exception as e:
                logging.warning(f"GMB lookup error for {user_id}: {e}")

        # Формируем текст
        if gmb_info and (gmb_info.get('balance') is not None or gmb_info.get('client', {}).get('balance') is not None):
            # Клиент найден в GMB — показываем баланс
            client_data = gmb_info.get('client', gmb_info)
            balance = client_data.get('balance', 0)
            name_gmb = client_data.get('name', full_name)
            k_bonus = client_data.get('k_bonus', 0)
            max_pay = client_data.get('maxPayBonusK', 0)

            # Доступные подарки
            gifts = client_data.get('gifts', [])
            available_gifts = [g for g in gifts if g.get('can_use')]

            loyalty_text = (
                f"🎁 <b>Твоя карта лояльности</b>\n\n"
                f"👤 {name_gmb}\n"
                f"💰 Баланс: <b>{balance} бонусов</b>\n"
            )
            if k_bonus:
                loyalty_text += f"📊 Кэшбэк: {k_bonus}% с каждого заказа\n"
            if max_pay:
                loyalty_text += f"💳 Оплата бонусами: до {max_pay}% от заказа\n"

            if available_gifts:
                loyalty_text += "\n🎁 <b>Доступные подарки:</b>\n"
                for g in available_gifts[:5]:
                    loyalty_text += f"  • {g.get('name', '???')} — {g.get('price', '?')} бонусов\n"

            loyalty_text += "\n👇 Открой карту, чтобы показать QR-код бармену:"
        else:
            # Клиент не найден или GMB не настроен — старое поведение
            loyalty_text = (
                "🎁 <b>Система Лояльности Евгенича!</b>\n\n"
                "Евгенич дарит тебе <b>500 рублей</b> 💸 на карту лояльности!\n\n"
                "Копи бонусы с каждого заказа и трать их на любимые напитки 🥃\n\n"
                "Жми кнопку ниже 👇 и регистрируй свою карту!"
            )

        # Отправляем сообщение с кнопкой регистрации
        bot.send_message(
            message.chat.id,
            loyalty_text,
            parse_mode="HTML",
            reply_markup=keyboards.get_loyalty_keyboard()
        )

        # Отправляем данные гостя в чат бота лояльности @spasibo_EVGENICH_bot
        try:
            contact_info = f"📋 Новый запрос карты лояльности:\n\n"
            contact_info += f"👤 Имя: {full_name}\n"
            contact_info += f"🆔 Telegram ID: {user_id}\n"
            if username:
                contact_info += f"📱 Username: @{username}\n"
            if phone:
                contact_info += f"📞 Телефон: {phone}\n"
            contact_info += f"\n🔗 Источник: Кнопка в боте @evgenichspbbot"

            # Отправляем уведомление в REPORT_CHAT_ID чтобы админы видели
            try:
                bot.send_message(REPORT_CHAT_ID, contact_info)
            except Exception as e:
                logging.error(f"Ошибка отправки контакта лояльности в отчёт: {e}")
        except Exception as e:
            logging.error(f"Ошибка обработки контакта лояльности: {e}")

    @bot.message_handler(func=lambda message: message.text == "🎮 Игры и развлечения")
    def handle_games_button(message: types.Message):
        """Обрабатывает кнопку игр и развлечений."""
        # В групповых чатах игры только для боссов/админов
        if message.chat.type != 'private':
            from core.config import ALL_ADMINS
            if message.from_user.id not in ALL_ADMINS:
                bot.reply_to(message, "🔒 Игры доступны только в личных сообщениях! Напиши мне в личку: @evgenichspbbot")
                return
        
        user_id = message.from_user.id
        try:
            from modules.games import get_user_game_stats, can_play_game

            # Получаем статистику игр пользователя
            stats = get_user_game_stats(user_id)
            
            if "error" in stats:
                bot.send_message(user_id, "Не удалось загрузить статистику игр.")
                return

            # Проверяем доступность игр
            quiz_status = can_play_game(user_id, "quiz")
            wheel_status = can_play_game(user_id, "wheel")

            # Формируем сообщение со статистикой и доступными играми
            games_text = f"""🎮 **Игры и развлечения от Евгенича**

🎯 **Ваша статистика:**
• Всего игр: {stats['total_games']}
• Викторин: {stats['quiz_games']} (правильно: {stats['quiz_correct']})
• Вращений колеса: {stats['wheel_spins']}
• Призов выиграно: {stats['prizes_won']}
• Не забрано призов: {stats['unclaimed_prizes']}

🎲 **Доступные игры:**

🧠 **Викторина от Евгенича** (/quiz)
{quiz_status['message']}
Отвечайте на вопросы о баре и получайте баллы!

🎰 **Колесо фортуны** (/wheel)  
{wheel_status['message']}
Крутите колесо и выигрывайте призы!

💡 **Подсказка:** Используйте команды /quiz, /wheel или /games для быстрого доступа"""

            bot.send_message(
                user_id,
                games_text,
                parse_mode="Markdown",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            
        except Exception as e:
            logging.error(f"Ошибка при обработке кнопки игр для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Не удалось загрузить игры. Попробуйте позже.")

    @bot.message_handler(func=lambda message: message.text == "🥃 Получить настойку по талону")
    def handle_redeem_nastoika(message: types.Message):
        """Обрабатывает кнопку получения настойки по талону - начинает сбор профиля."""
        # В групповых чатах получение настойки только для боссов/админов
        if message.chat.type != 'private':
            from core.config import ALL_ADMINS
            if message.from_user.id not in ALL_ADMINS:
                bot.reply_to(message, "🔒 Получение настойки доступно только в личных сообщениях! Напиши мне в личку: @evgenichspbbot 🥃")
                return
        
        user_id = message.from_user.id
        user_status = database.get_reward_status(user_id)
        
        if user_status in ['redeemed', 'redeemed_and_left']:
            bot.send_message(
                message.chat.id,
                "🥃 Твой купон уже был использован, товарищ! Если хочешь еще настойку, приводи друзей!",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            return
        
        if user_status == 'issued':
            # Купон уже выдан, показываем меню с кнопкой погашения
            bot.send_message(
                message.chat.id,
                "У тебя уже есть купон на настойку! 🥃\n\nПокажи этот экран бармену для получения настойки:",
                reply_markup=keyboards.get_redeem_keyboard()
            )
            return
        
        # Начинаем сбор профиля - запрашиваем контакт (БЕЗ проверки подписки!)
        bot.send_message(
            message.chat.id,
            texts.CONTACT_REQUEST_TEXT,
            reply_markup=keyboards.get_contact_request_keyboard()
        )

    @bot.message_handler(commands=['voice'])
    def handle_voice_command(message: types.Message):
        audio_id = settings_manager.get_setting("greeting_audio_id")
        if audio_id:
            try:
                bot.send_audio(message.chat.id, audio_id, caption="🎙️ Сообщение от Евгенича!")
            except Exception as e:
                bot.send_message(message.chat.id, "Что-то с плёнкой случилось, не могу найти запись... 😥")
        else:
            bot.send_message(message.chat.id, "Евгенич пока не записал для вас обращение, товарищ.")

    @bot.message_handler(commands=['help'])
    def handle_help_command(message: types.Message):
        bot.send_message(
            message.chat.id,
            texts.get_help_text(message.from_user.id, ALL_ADMINS),
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['restart'])
    def handle_restart_command(message: types.Message):
        """Команда для админов для сброса состояния пользователя (для тестирования)."""
        user_id = message.from_user.id
        
        if user_id in ALL_ADMINS:
            # Удаляем пользователя из базы данных
            success, msg = database.delete_user(user_id)
            
            # Очищаем состояние профиля, если есть
            if user_id in user_profile_data:
                del user_profile_data[user_id]
            
            bot.send_message(
                message.chat.id,
                f"✅ Успех: Пользователь {user_id} успешно удален из SQLite.\nМожете начинать тестирование заново с /start",
                reply_markup=types.ReplyKeyboardRemove()
            )
            logging.info(f"Админ {user_id} сбросил свое состояние через /restart")
        else:
            bot.send_message(message.chat.id, "🚫 Эта команда доступна только администраторам.")

    @bot.message_handler(content_types=['contact'])
    def handle_contact_received(message: types.Message):
        """Обрабатывает получение контакта от пользователя."""
        user_id = message.from_user.id
        
        if message.contact and message.contact.user_id == user_id:
            # Пользователь поделился своим контактом
            phone_number = message.contact.phone_number
            logging.info(f"Пользователь {user_id} поделился контактом: {phone_number}")
            
            # Сохраняем контакт в базу данных
            if database.update_user_contact(user_id, phone_number):
                # Благодарим за контакт
                bot.send_message(
                    message.chat.id,
                    texts.CONTACT_RECEIVED_TEXT
                )
                
                # Переходим к сбору имени
                user_profile_data[user_id] = 'awaiting_name'
                bot.send_message(
                    message.chat.id,
                    texts.NAME_REQUEST_TEXT,
                    reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "Произошла ошибка при сохранении контакта. Попробуйте еще раз.",
                    reply_markup=keyboards.get_contact_request_keyboard()
                )
        else:
            # Пользователь поделился чужим контактом
            bot.send_message(
                message.chat.id,
                "Пожалуйста, поделитесь своим контактом, а не чужим 😊\n\nДля этого нажмите кнопку ниже:",
                reply_markup=keyboards.get_contact_request_keyboard()
            )
    def handle_gift_button(message: types.Message):
        """Обрабатывает нажатие кнопки получения настойки."""
        user_id = message.from_user.id
        status = database.get_reward_status(user_id)
        
        if status == 'not_found':
            bot.send_message(user_id, "Сначала нужно зарегистрироваться! Нажми /start")
            return
        elif status in ['redeemed', 'redeemed_and_left']:
            bot.send_message(
                user_id,
                texts.ALREADY_REDEEMED_TEXT,
                reply_markup=keyboards.get_main_menu_keyboard(user_id),
                parse_mode="Markdown"
            )
            return
        
        # Проверяем данные пользователя
        user_data = database.find_user_by_id(user_id)
        
        if not user_data or not user_data['phone_number']:
            # Контакта нет, запрашиваем его сначала
            bot.send_message(
                user_id,
                texts.CONTACT_REQUEST_TEXT,
                reply_markup=keyboards.get_contact_request_keyboard()
            )
        elif not user_data['real_name'] or not user_data['birth_date']:
            # Контакт есть, но нет полного профиля - запрашиваем имя
            user_profile_data[user_id] = 'awaiting_name'
            bot.send_message(
                user_id,
                texts.NAME_REQUEST_TEXT
            )
        else:
            # Полный профиль есть, показываем подсказку о подписке на канал
            # ЖЁСТКАЯ ПРИВЯЗКА: используем сохранённый payload
            saved_payload = user_current_payload.get(user_id, '')
            channel_to_show = get_channel_for_payload(saved_payload)
            logging.info(f"🎯 Профиль готов для {user_id}: payload='{saved_payload}', канал={channel_to_show}")
            bot.send_message(
                user_id,
                texts.SUBSCRIBE_PROMPT_TEXT,
                reply_markup=keyboards.get_subscription_keyboard(f"https://t.me/{channel_to_show.replace('@', '')}")
            )
    def handle_get_gift_press(message: types.Message):
        user_id = message.from_user.id
        status = database.get_reward_status(user_id)
        if status in ['issued', 'redeemed', 'redeemed_and_left']:
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return
        
        # ЖЁСТКАЯ ПРИВЯЗКА: используем сохранённый payload
        saved_payload = user_current_payload.get(user_id, '')
        channel_to_check = get_channel_for_payload(saved_payload)
        logging.info(f"🎯 handle_get_gift_press для {user_id}: payload='{saved_payload}', канал={channel_to_check}")
        
        try:
            chat_member = bot.get_chat_member(chat_id=channel_to_check, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.send_message(user_id, texts.SUBSCRIPTION_SUCCESS_TEXT)
                issue_coupon(bot, user_id, message.chat.id)
                return
        except Exception:
            pass
        channel_url = f"https://t.me/{channel_to_check.lstrip('@')}"
        try:
            bot.send_sticker(message.chat.id, HELLO_STICKER_ID)
        except Exception:
            pass
        bot.send_message(
            message.chat.id,
            texts.SUBSCRIBE_PROMPT_TEXT,
            reply_markup=keyboards.get_subscription_keyboard(channel_url),
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: message.content_type == 'text' and message.from_user.id in user_profile_data)
    def handle_profile_data_collection(message: types.Message):
        """Обрабатывает сбор данных профиля пользователя (имя и дата рождения)."""
        user_id = message.from_user.id
        state = user_profile_data.get(user_id)
        
        if state == 'awaiting_name':
            # Пользователь вводит имя
            real_name = message.text.strip()
            
            if len(real_name) < 2 or len(real_name) > 50:
                bot.send_message(
                    message.chat.id,
                    "Имя должно быть от 2 до 50 символов. Попробуйте еще раз:"
                )
                return
            
            # Сохраняем имя
            if database.update_user_name(user_id, real_name):
                bot.send_message(
                    message.chat.id,
                    texts.NAME_RECEIVED_TEXT
                )
                
                # Переходим к сбору даты рождения
                user_profile_data[user_id] = 'awaiting_birth_date'
                bot.send_message(
                    message.chat.id,
                    texts.BIRTH_DATE_REQUEST_TEXT,
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "Произошла ошибка при сохранении имени. Попробуйте еще раз:"
                )
        
        elif state == 'awaiting_birth_date':
            # Пользователь вводит дату рождения
            birth_date_text = message.text.strip()
            
            # Проверяем формат даты
            try:
                import re
                if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birth_date_text):
                    raise ValueError("Неверный формат")
                
                # Проверяем валидность даты
                day, month, year = map(int, birth_date_text.split('.'))
                birth_date = datetime.date(year, month, day)
                
                # Проверяем, что дата не в будущем и не слишком старая
                today = datetime.date.today()
                if birth_date > today:
                    bot.send_message(
                        message.chat.id,
                        "Дата рождения не может быть в будущем! Попробуйте еще раз:"
                    )
                    return
                
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age > 100:
                    bot.send_message(
                        message.chat.id,
                        "Кажется, дата слишком давняя. Проверьте и попробуйте еще раз:"
                    )
                    return
                
                # Сохраняем дату рождения
                if database.update_user_birth_date(user_id, birth_date_text):
                    # Завершаем сбор данных
                    del user_profile_data[user_id]
                    
                    bot.send_message(
                        message.chat.id,
                        texts.PROFILE_COMPLETED_TEXT
                    )
                    
                    # ЖЁСТКАЯ ПРИВЯЗКА: определяем канал по сохранённому payload
                    saved_payload = user_current_payload.get(user_id, '')
                    
                    # === ВЫБОР ГОРОДА для qr_bar (один QR на два города) ===
                    if saved_payload == 'qr_bar':
                        logging.info(f"🏙 Показываем выбор города для {user_id} после заполнения профиля")
                        city_markup = types.InlineKeyboardMarkup(row_width=1)
                        city_markup.add(
                            types.InlineKeyboardButton("🏛 Санкт-Петербург", callback_data="city_select_spb"),
                            types.InlineKeyboardButton("🏙 Москва", callback_data="city_select_msk")
                        )
                        bot.send_message(
                            message.chat.id,
                            "📍 В каком городе ты хочешь к нам заглянуть?",
                            reply_markup=city_markup
                        )
                    else:
                        # Обычный флоу — сразу показываем подписку
                        channel_to_show = get_channel_for_payload(saved_payload)
                        channel_url = f"https://t.me/{channel_to_show.lstrip('@')}"
                        
                        logging.info(f"🎯 ПОКАЗ КНОПКИ ПОДПИСКИ для {user_id}:")
                        logging.info(f"   - Сохранённый payload: '{saved_payload}'")
                        logging.info(f"   - Выбранный канал: {channel_to_show}")
                        logging.info(f"   - URL кнопки: {channel_url}")
                        
                        bot.send_message(
                            message.chat.id,
                            texts.SUBSCRIBE_PROMPT_TEXT,
                            reply_markup=keyboards.get_subscription_keyboard(channel_url)
                        )
                else:
                    bot.send_message(
                        message.chat.id,
                        "Произошла ошибка при сохранении даты рождения. Попробуйте еще раз:"
                    )
                    
            except (ValueError, TypeError):
                bot.send_message(
                    message.chat.id,
                    texts.BIRTH_DATE_ERROR_TEXT,
                    parse_mode="Markdown"
                )
    
    @bot.message_handler(commands=['recommend'])
    def handle_recommend(message: types.Message):
        """
        Обрабатывает команду /recommend и предоставляет персонализированные рекомендации.
        """
        user_id = message.from_user.id
        try:
            from ai.assistant import analyze_guest_preferences

            # Получаем рекомендации для пользователя
            recommendations = analyze_guest_preferences(user_id)

            # Отправляем рекомендации пользователю
            bot.send_message(
                user_id,
                recommendations,
                parse_mode="Markdown",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
        except Exception as e:
            logging.error(f"Ошибка при обработке команды /recommend для пользователя {user_id}: {e}")
            bot.send_message(
                user_id,
                "Не удалось загрузить ваши рекомендации. Попробуйте позже.",
                parse_mode="Markdown"
            )

    @bot.message_handler(commands=['quiz'])
    def handle_quiz(message: types.Message):
        """
        Обрабатывает команду /quiz - запуск викторины.
        """
        user_id = message.from_user.id
        try:
            from modules.games import can_play_game, get_random_quiz_question, QUIZ_QUESTIONS

            # Проверяем, может ли пользователь играть
            can_play = can_play_game(user_id, "quiz")
            if not can_play["can_play"]:
                bot.send_message(user_id, can_play["message"])
                return

            # Получаем случайный вопрос
            question = get_random_quiz_question()
            
            # Создаем клавиатуру с вариантами ответов
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            for i, option in enumerate(question["options"]):
                callback_data = f"quiz_answer_{QUIZ_QUESTIONS.index(question)}_{i}"
                keyboard.add(types.InlineKeyboardButton(option, callback_data=callback_data))
            
            # Отправляем вопрос
            bot.send_message(
                user_id,
                f"🧠 **Викторина от Евгенича**\n\n{question['question']}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logging.error(f"Ошибка при запуске викторины для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Не удалось запустить викторину. Попробуйте позже.")

    @bot.message_handler(commands=['wheel'])
    def handle_wheel(message: types.Message):
        """
        Обрабатывает команду /wheel - запуск колеса фортуны.
        """
        user_id = message.from_user.id
        try:
            from modules.games import can_play_game, spin_wheel_of_fortune, save_game_result

            # Проверяем, может ли пользователь играть
            can_play = can_play_game(user_id, "wheel")
            if not can_play["can_play"]:
                bot.send_message(user_id, can_play["message"])
                return

            # Крутим колесо
            result = spin_wheel_of_fortune()
            
            # Сохраняем результат
            save_game_result(user_id, "wheel", result)
            
            # Отправляем результат
            message_text = f"{result['message']}\n\n"
            if result["claim_code"]:
                message_text += f"🎫 Код для получения: `{result['claim_code']}`\n"
                message_text += "Покажите этот код администратору или сотруднику."
            
            bot.send_message(
                user_id,
                message_text,
                parse_mode="Markdown",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            
        except Exception as e:
            logging.error(f"Ошибка при запуске колеса фортуны для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Не удалось запустить колесо фортуны. Попробуйте позже.")

    @bot.message_handler(commands=['games'])
    def handle_games_menu(message: types.Message):
        """
        Обрабатывает команду /games - показывает меню игр и статистику.
        """
        user_id = message.from_user.id
        try:
            from modules.games import get_user_game_stats

            # Получаем статистику игр пользователя
            stats = get_user_game_stats(user_id)
            
            if "error" in stats:
                bot.send_message(user_id, "Не удалось загрузить статистику игр.")
                return

            # Формируем сообщение со статистикой
            stats_text = f"""🎮 **Игровое меню**

📊 **Ваша статистика:**
🎯 Всего игр: {stats['total_games']}
🧠 Викторин: {stats['quiz_games']} (правильно: {stats['quiz_correct']})
🎰 Вращений колеса: {stats['wheel_spins']}
🎁 Призов выиграно: {stats['prizes_won']}
🎫 Не забрано призов: {stats['unclaimed_prizes']}

🎲 **Доступные игры:**
/quiz - Викторина (каждый час)
/wheel - Колесо фортуны (каждые 3 часа)"""

            bot.send_message(
                user_id,
                stats_text,
                parse_mode="Markdown",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            
        except Exception as e:
            logging.error(f"Ошибка при показе меню игр для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Не удалось загрузить меню игр. Попробуйте позже.")

    @bot.message_handler(commands=['password'])
    def handle_password_command(message: types.Message):
        """
        Обрабатывает команду /password для получения информации о пароле дня.
        """
        user_id = message.from_user.id
        try:
            from modules.daily_activities import get_password_of_the_day, get_user_password_stats

            # Получаем статистику пользователя
            stats = get_user_password_stats(user_id)
            
            if "error" in stats:
                bot.send_message(user_id, "Не удалось загрузить информацию о пароле.")
                return

            # Получаем информацию о пароле дня
            password_info = get_password_of_the_day()
            
            if stats["correct_today"]:
                message_text = f"""🔐 **Секретный пароль дня**

✅ Сегодня вы уже угадали пароль!
🎁 Ваша награда: {password_info['reward']}

Новый пароль будет доступен завтра в 00:00"""
            elif not stats["can_try"]:
                message_text = f"""🔐 **Секретный пароль дня**

❌ Сегодня вы исчерпали попытки угадать пароль.
Новый пароль будет доступен завтра в 00:00

💡 Подсказка для завтра: следите за нашими новостями!"""
            else:
                # Активируем режим ввода пароля
                password_attempts[user_id] = True
                
                message_text = f"""🔐 **Секретный пароль дня**

🗓 Дата: {password_info['date']}
🎁 Награда: {password_info['reward']}
💡 {password_info['hint']}

Попытки сегодня: {stats['attempts_today']}

Введите пароль в следующем сообщении:"""

            bot.send_message(
                user_id,
                message_text,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logging.error(f"Ошибка при обработке команды пароля для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Не удалось загрузить информацию о пароле. Попробуйте позже.")

    @bot.message_handler(commands=['events'])
    def handle_events_command(message: types.Message):
        """
        Обрабатывает команду /events для просмотра предстоящих мероприятий.
        """
        user_id = message.from_user.id
        try:
            from modules.daily_activities import get_upcoming_events

            # Получаем список предстоящих мероприятий
            events = get_upcoming_events()
            
            if not events:
                message_text = """🎪 **Мероприятия в баре**

В ближайшие дни мероприятий не запланировано.

Следите за обновлениями в нашем Telegram-канале! 📢"""
            else:
                message_text = "🎪 **Предстоящие мероприятия**\n\n"
                
                for event in events:
                    event_date = datetime.fromisoformat(event['event_date'].replace(' ', 'T'))
                    date_str = event_date.strftime('%d.%m.%Y в %H:%M')
                    
                    message_text += f"""📅 **{event['title']}**
🗓 {date_str}
📝 {event['description']}
👥 Участников: {event['current_participants']}

Для регистрации: /register_{event['id']}

---

"""
                
                message_text += "💡 Используйте команду /register_[ID] для регистрации на мероприятие"

            bot.send_message(
                user_id,
                message_text,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logging.error(f"Ошибка при показе мероприятий для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Не удалось загрузить мероприятия. Попробуйте позже.")

    # Обработчик для ввода секретного пароля
    password_attempts = {}  # Словарь для отслеживания состояния ввода пароля
    
    @bot.message_handler(func=lambda message: message.from_user.id in password_attempts and message.content_type == 'text')
    def handle_password_input(message: types.Message):
        """
        Обрабатывает ввод секретного пароля пользователем.
        """
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        try:
            from modules.daily_activities import check_daily_password, save_password_attempt, get_user_password_stats

            # Проверяем пароль
            result = check_daily_password(user_input)
            
            # Сохраняем попытку
            save_password_attempt(user_id, user_input, result["is_correct"])
            
            # Отправляем результат
            bot.send_message(
                user_id,
                result["message"],
                parse_mode="Markdown",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            
            # Убираем пользователя из режима ввода пароля
            if user_id in password_attempts:
                del password_attempts[user_id]
            
        except Exception as e:
            logging.error(f"Ошибка при проверке пароля для пользователя {user_id}: {e}")
            bot.send_message(user_id, "Произошла ошибка при проверке пароля. Попробуйте позже.")
            if user_id in password_attempts:
                del password_attempts[user_id]
