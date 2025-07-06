# /handlers/user_commands.py

import logging
from telebot import types

# Импортируем конфиги и утилиты
from config import CHANNEL_ID, HELLO_STICKER_ID, NASTOYKA_STICKER_ID, ADMIN_IDS
import g_sheets

# Импортируем наши тексты и клавиатуры
import texts
import keyboards

# --- Вспомогательные функции ---

def issue_coupon(bot, user_id, chat_id):
    """Выдает пользователю купон на настойку."""
    g_sheets.update_status(user_id, 'issued')
    
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
    """Регистрирует обработчики для основных команд пользователя."""

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """
        Обрабатывает команду /start, регистрирует нового пользователя или показывает главное меню.
        """
        logging.info(f"Пользователь {message.from_user.id} нажал /start с текстом: {message.text}")
        user_id = message.from_user.id
        status = g_sheets.get_reward_status(user_id)
        
        if status == 'redeemed':
            logging.info(f"Пользователь {user_id} уже получал награду. Показываем основное меню.")
            bot.send_message(
                user_id, 
                texts.ALREADY_REDEEMED_TEXT,
                reply_markup=keyboards.get_main_menu_keyboard(user_id), 
                parse_mode="Markdown"
            )
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
                else:
                    allowed_sources = {
                        'qr_tv': 'QR с ТВ', 'qr_bar': 'QR на баре', 
                        'qr_toilet': 'QR в туалете', 'vk': 'VK', 
                        'inst': 'Instagram', 'flyer': 'Листовки', 'site': 'Сайт'
                    }
                    if payload in allowed_sources:
                        source = allowed_sources[payload]
            
            g_sheets.add_new_user(user_id, message.from_user.username or "N/A", message.from_user.first_name, source, referrer_id)
            if referrer_id:
                bot.send_message(user_id, texts.NEW_USER_REFERRED_TEXT)

        bot.send_message(
            message.chat.id, 
            texts.WELCOME_TEXT, 
            reply_markup=keyboards.get_gift_keyboard()
        )

    @bot.message_handler(commands=['friend'])
    @bot.message_handler(func=lambda message: message.text == "🤝 Привести товарища")
    def handle_friend_command(message: types.Message):
        """
        Генерирует и отправляет пользователю его персональную реферальную ссылку в виде текста.
        """
        user_id = message.from_user.id
        logging.info(f"Пользователь {user_id} запросил реферальную ссылку.")

        try:
            bot_username = bot.get_me().username
            ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

            bot.send_message(user_id, texts.FRIEND_PROMPT_TEXT)
            # Отправляем ссылку как форматированный код для легкого копирования
            bot.send_message(user_id, f"`{ref_link}`", parse_mode="Markdown")
            # Отправляем правила акции
            bot.send_message(user_id, texts.FRIEND_RULES_TEXT, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"Критическая ошибка при создании реферальной ссылки для {user_id}: {e}", exc_info=True)
            bot.send_message(user_id, "Что-то пошло не так. Администратор уже разбирается.")

    @bot.message_handler(commands=['channel'])
    def handle_channel_command(message: types.Message):
        """
        Отправляет пользователю ссылку на основной Telegram-канал.
        """
        logging.info(f"Пользователь {message.from_user.id} запросил ссылку на канал.")
        channel_url = f"https.me/{CHANNEL_ID.lstrip('@')}"
        keyboard = types.InlineKeyboardMarkup()
        url_button = types.InlineKeyboardButton(text="➡️ Перейти на канал", url=channel_url)
        keyboard.add(url_button)
        bot.send_message(message.chat.id, "Вот ссылка на наш основной канал:", reply_markup=keyboard)

    @bot.message_handler(commands=['menu'])
    @bot.message_handler(func=lambda message: message.text == "📖 Меню")
    def handle_menu_command(message: types.Message):
        """
        Показывает пользователю кнопки для выбора меню.
        """
        logging.info(f"Пользователь {message.from_user.id} открыл меню.")
        bot.send_message(
            message.chat.id, 
            texts.MENU_PROMPT_TEXT, 
            reply_markup=keyboards.get_menu_choice_keyboard()
        )
        
    @bot.message_handler(commands=['secret'])
    def handle_secret_command(message: types.Message):
        """Показывает пользователю актуальное секретное слово."""
        logging.info(f"Пользователь {message.from_user.id} запросил секретное слово.")
        secret_data = g_sheets.get_secret_word_data()
        bot.send_message(message.chat.id, texts.SECRET_WORD_PROMPT)
        bot.send_message(message.chat.id, texts.get_secret_word_text(secret_data), parse_mode="Markdown")

    @bot.message_handler(commands=['help'])
    def handle_help_command(message: types.Message):
        """
        Отправляет справочное сообщение с описанием команд бота.
        """
        bot.send_message(
            message.chat.id, 
            texts.get_help_text(message.from_user.id, ADMIN_IDS), 
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: message.text == "🥃 Получить настойку по талону")
    def handle_get_gift_press(message: types.Message):
        """
        Запускает воронку получения настойки за подписку.
        """
        user_id = message.from_user.id
        status = g_sheets.get_reward_status(user_id)
        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return
        
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.send_message(user_id, texts.SUBSCRIPTION_SUCCESS_TEXT)
                issue_coupon(bot, user_id, message.chat.id)
                return
        except Exception as e:
            logging.warning(f"Ошибка при предварительной проверке подписки для {user_id}: {e}")
        
        channel_url = f"https.me/{CHANNEL_ID.lstrip('@')}"
        try:
            bot.send_sticker(message.chat.id, HELLO_STICKER_ID)
        except Exception as e:
            logging.error(f"Не удалось отправить приветственный стикер: {e}")
            
        bot.send_message(
            message.chat.id, 
            texts.SUBSCRIBE_PROMPT_TEXT, 
            reply_markup=keyboards.get_subscription_keyboard(channel_url),
            parse_mode="Markdown"
        )
