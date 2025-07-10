# /handlers/user_commands.py

import logging
from telebot import types

from config import CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, ADMIN_IDS, REPORT_CHAT_ID
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

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """
        Обрабатывает команду /start, регистрирует нового пользователя или показывает главное меню.
        """
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
                logging.info(f"Обнаружена нагрузка (payload): {payload}")

                if payload.startswith('w_'):
                    staff_code = payload.replace('w_', '')
                    staff_member = database.find_staff_by_code(staff_code)
                    if staff_member:
                        brought_by_staff_id = staff_member['staff_id']
                        source = f"Сотрудник: {staff_member['short_name']}"
                    else:
                        logging.warning(f"Не найден активный сотрудник с кодом {staff_code}")
                elif payload.startswith('ref_'):
                    try:
                        referrer_id = int(payload.replace('ref_', ''))
                        source = 'Реферал'
                    except (ValueError, IndexError):
                        logging.warning(f"Не удалось распознать ref_id из {payload}")
                else:
                    allowed_sources = {
                        'qr_tv': 'QR с ТВ', 'qr_bar': 'QR на баре', 'qr_toilet': 'QR в туалете',
                        'vk': 'VK', 'inst': 'Instagram', 'flyer': 'Листовки',
                        'site': 'Сайт', 'qr_waiter': 'QR от официанта', 'taplink': 'Taplink'
                    }
                    if payload in allowed_sources:
                        source = allowed_sources[payload]

            database.add_new_user(user_id, message.from_user.username, message.from_user.first_name, source, referrer_id, brought_by_staff_id)
            if referrer_id:
                bot.send_message(user_id, texts.NEW_USER_REFERRED_TEXT)

        bot.send_message(
            message.chat.id,
            texts.WELCOME_TEXT,
            reply_markup=keyboards.get_gift_keyboard()
        )

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
            texts.get_help_text(message.from_user.id, ADMIN_IDS),
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: message.text == "🥃 Получить настойку по талону")
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
