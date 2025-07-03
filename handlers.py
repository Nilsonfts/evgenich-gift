# handlers.py
import logging
from telebot import types
from config import CHANNEL_ID
from database import user_exists, add_user, check_reward_status, grant_reward
from g_sheets import add_subscription_to_sheet

def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """Отправляет приветствие и постоянную кнопку."""
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        get_gift_button = types.KeyboardButton("🎁 ПОЛУЧИТЬ НАСТОЙКУ")
        keyboard.add(get_gift_button)
        bot.send_message(message.chat.id, 
                         "Привет! 👋 Нажми на кнопку ниже, чтобы получить свой подарок.", 
                         reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == "🎁 ПОЛУЧИТЬ НАСТОЙКУ")
    def handle_get_gift_press(message: types.Message):
        """Обрабатывает нажатие на кнопку 'ПОЛУЧИТЬ НАСТОЙКУ'."""
        user_id = message.from_user.id
        username = message.from_user.username or "N/A"
        first_name = message.from_user.first_name

        if not user_exists(user_id):
            add_user(user_id, username, first_name)
            logging.info(f"Новый пользователь: {first_name} (@{username}, {user_id})")

        if check_reward_status(user_id):
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return

        welcome_text = (
            "Отлично! 👍\n\n"
            "Чтобы получить настойку, подпишись на наш телеграм-канал. Это займет всего секунду.\n\n"
            "Когда подпишешься — нажимай на кнопку «Я подписался» здесь же."
        )

        inline_keyboard = types.InlineKeyboardMarkup()
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        subscribe_button = types.InlineKeyboardButton(text="➡️ Перейти к каналу", url=channel_url)
        check_button = types.InlineKeyboardButton(text="✅ Я подписался, проверить!", callback_data="check_subscription")
        inline_keyboard.add(subscribe_button).add(check_button)
        
        try:
            with open('welcome.jpg', 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")
        except FileNotFoundError:
            logging.warning("Файл welcome.jpg не найден. Отправляю текстовое приветствие.")
            bot.send_message(message.chat.id, welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")


    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        """Обрабатывает нажатие на inline-кнопку проверки подписки."""
        user_id = call.from_user.id

        if check_reward_status(user_id):
            bot.answer_callback_query(call.id)
            bot.edit_message_caption("Вы уже получали свой подарок. Спасибо, что вы с нами! 😉",
                                     call.message.chat.id, call.message.message_id)
            return

        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.answer_callback_query(call.id, "Отлично, подписка есть! ✅")
                
                # Выдаем награду и отправляем данные в гугл
                grant_reward(user_id)
                add_subscription_to_sheet(user_id, call.from_user.username or "N/A", call.from_user.first_name)

                coupon_text = (
                    "🎉 Поздравляем! 🎉\n\n"
                    "Ваш подарок - **фирменная настойка**.\n"
                    "Покажите это сообщение бармену, чтобы получить свой приз. Награда выдается один раз."
                )
                
                # Убираем кнопки из старого сообщения
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                
                try:
                    with open('tincture.jpg', 'rb') as photo:
                        bot.send_photo(user_id, photo, caption=coupon_text, parse_mode="Markdown")
                except FileNotFoundError:
                    logging.warning("Файл tincture.jpg не найден. Отправляю текстовый купон.")
                    bot.send_message(user_id, coupon_text, parse_mode="Markdown")

            else:
                bot.answer_callback_query(call.id, "Похоже, вы еще не подписались. Попробуйте снова.", show_alert=True)

        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)
