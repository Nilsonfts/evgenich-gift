# /handlers/user_commands.py

import logging
import datetime
from telebot import types

from config import CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, ALL_ADMINS, REPORT_CHAT_ID
import database
import settings_manager
import texts
import keyboards
from qr_generator import create_qr_code

# --- Вспомогательные функции ---

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
            "rvv": "РВВ (Руки Вверх Винтаж)",
            "evgenich": "ЕВГЕНИЧ (Классический)", 
            "nebar": "НЕБАР (Необычный барный стиль)",
            "spletni": "СПЛЕТНИ (Дружеская болтовня)",
            "orbita": "ОРБИТА (Космический стиль)"
        }
        
        current_name = concept_names.get(current_concept, "не выбрана")
        
        bot.send_message(
            message.chat.id,
            f"🎭 **Мастер настройки чата**\n\n"
            f"Выберите концепцию для этого чата:\n\n"
            f"Текущая концепция: **{current_name}**",
            reply_markup=keyboards.get_concept_choice_keyboard(),
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """
        Обрабатывает команду /start, регистрирует нового пользователя или показывает главное меню.
        """
        try:
            user_id = message.from_user.id
            status = database.get_reward_status(user_id)

            if status in ['redeemed', 'redeemed_and_left']:
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
                                REPORT_CHAT_ID,
                                f"📊 QR-переход: Новый гость привлечен сотрудником {staff_member['short_name']} "
                                f"(@{message.from_user.username or 'без_username'})",
                                parse_mode="Markdown"
                            )
                        else:
                            logging.warning(f"❌ QR-код сотрудника некорректен! Код '{staff_code}' не найден в базе активных сотрудников. Переход засчитан как 'direct'.")
                            # При неправильном коде сотрудника считаем переход "прямым"
                            source = 'direct'
                            brought_by_staff_id = None
                    elif payload.startswith('ref_'):
                        try:
                            referrer_id = int(payload.replace('ref_', ''))
                            source = 'Реферал'
                            logging.info(f"Пользователь {user_id} приглашен рефералом {referrer_id}")
                        except (ValueError, IndexError):
                            logging.warning(f"Не удалось распознать ref_id из {payload}")
                    else:
                        allowed_sources = {
                            'qr_tv': 'QR-код на ТВ', 
                            'qr_bar': 'QR-код на баре', 
                            'qr_waiter': 'QR от официанта',
                            'vk': 'Ссылка из ВКонтакте', 
                            'inst': 'Ссылка из Instagram', 
                            'menu': 'Меню в баре',
                            'flyer': 'Листовка на улице', 
                            'streat': 'Уличное Меню',
                            '2gis': '2ГИС Кнопка',
                            'site': 'Кнопка Сайт',
                            'taplink': 'Таплинк на ТВ'
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

            # Отправляем приветствие
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
            except:
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


    # --- Остальные команды без изменений ---

    @bot.message_handler(commands=['friend'])
    @bot.message_handler(func=lambda message: message.text == "🤝 Привести товарища")
    def handle_friend_command(message: types.Message):
        user_id = message.from_user.id
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        bot.send_message(user_id, texts.FRIEND_PROMPT_TEXT)
        bot.send_message(user_id, f"`{ref_link}`", parse_mode="Markdown")
        bot.send_message(user_id, texts.FRIEND_RULES_TEXT, parse_mode="Markdown")

    @bot.message_handler(commands=['menu'])
    @bot.message_handler(func=lambda message: message.text == "📖 Меню")
    def handle_menu_command(message: types.Message):
        bot.send_message(
            message.chat.id,
            texts.MENU_PROMPT_TEXT,
            reply_markup=keyboards.get_menu_choice_keyboard()
        )

    @bot.message_handler(func=lambda message: message.text == "🎮 Игры и развлечения")
    def handle_games_button(message: types.Message):
        """Обрабатывает кнопку игр и развлечений."""
        user_id = message.from_user.id
        try:
            from games import get_user_game_stats, can_play_game

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
        user_id = message.from_user.id
        user_status = database.get_reward_status(user_id)
        
        if user_status in ['redeemed', 'redeemed_and_left']:
            bot.send_message(
                message.chat.id,
                "🥃 Твой купон уже был использован, товарищ! Если хочешь еще настойку, приводи друзей!",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            return
        
        # Начинаем сбор профиля - запрашиваем контакт
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
            bot.send_message(
                user_id,
                texts.SUBSCRIBE_PROMPT_TEXT,
                reply_markup=keyboards.get_subscription_keyboard(f"https://t.me/{CHANNEL_ID.replace('@', '')}")
            )
    def handle_get_gift_press(message: types.Message):
        user_id = message.from_user.id
        status = database.get_reward_status(user_id)
        if status in ['issued', 'redeemed', 'redeemed_and_left']:
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.send_message(user_id, texts.SUBSCRIPTION_SUCCESS_TEXT)
                issue_coupon(bot, user_id, message.chat.id)
                return
        except Exception:
            pass
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
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
                    
                    # Переходим к подписке на канал
                    bot.send_message(
                        message.chat.id,
                        texts.SUBSCRIBE_PROMPT_TEXT,
                        reply_markup=keyboards.get_subscription_keyboard(f"https://t.me/{CHANNEL_ID.replace('@', '')}")
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
            from games import can_play_game, get_random_quiz_question, QUIZ_QUESTIONS

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
            from games import can_play_game, spin_wheel_of_fortune, save_game_result

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
            from games import get_user_game_stats

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
            from daily_activities import get_password_of_the_day, get_user_password_stats

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
            from daily_activities import get_upcoming_events

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
            from daily_activities import check_daily_password, save_password_attempt, get_user_password_stats

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
