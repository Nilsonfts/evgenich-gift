import logging
from telebot import types
from config import CHANNEL_ID
from database import add_user, get_reward_status, grant_reward, redeem_reward
from g_sheets import add_subscription_to_sheet

def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """Отправляет приветствие и постоянную кнопку 'Получить настойку'."""
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        get_gift_button = types.KeyboardButton("🎁 ПОЛУЧИТЬ НАСТОЙКУ")
        keyboard.add(get_gift_button)
        
        bot.send_message(message.chat.id, 
                         "Привет! 👋 Нажми на кнопку ниже, чтобы получить свой подарок.", 
                         reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == "🎁 ПОЛУЧИТЬ НАСТОЙКУ")
    def handle_get_gift_press(message: types.Message):
        """Обрабатывает нажатие на кнопку и просит подписаться на канал."""
        user_id = message.from_user.id
        username = message.from_user.username or "N/A"
        first_name = message.from_user.first_name

        add_user(user_id, username, first_name)

        if get_reward_status(user_id) in ['issued', 'redeemed']:
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
        inline_keyboard.add(subscribe_button)
        inline_keyboard.add(check_button)
        
        try:
            with open('welcome.jpg', 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")
        except FileNotFoundError:
            logging.warning("Файл welcome.jpg не найден. Отправляю текстовое приветствие.")
            bot.send_message(message.chat.id, welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        """Проверяет подписку и выдает купон с кнопкой погашения."""
        user_id = call.from_user.id
        
        if get_reward_status(user_id) in ['issued', 'redeemed']:
            bot.answer_callback_query(call.id, "Вы уже получали свой подарок.", show_alert=True)
            return

        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

            if chat_member.status in ['member', 'administrator', 'creator']:
                grant_reward(user_id)
                add_subscription_to_sheet(user_id, call.from_user.username or "N/A", call.from_user.first_name)

                coupon_text = (
                    "🎉 Поздравляем! 🎉\n\n"
                    "Вы получили фирменную настойку!\n\n"
                    "**ВАЖНО:** Не нажимайте кнопку самостоятельно!\n"
                    "1. Покажите этот экран бармену.\n"
                    "2. Нажмите кнопку **только** по его просьбе."
                )
                
                redeem_keyboard = types.InlineKeyboardMarkup()
                redeem_button = types.InlineKeyboardButton(
                    text="🔒 Награда заблокирована (нажать при бармене)", 
                    callback_data="redeem_reward"
                )
                redeem_keyboard.add(redeem_button)

                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                try:
                    with open('tincture.jpg', 'rb') as photo:
                        bot.send_photo(user_id, photo, caption=coupon_text, parse_mode="Markdown", reply_markup=redeem_keyboard)
                except FileNotFoundError:
                    bot.send_message(user_id, coupon_text, parse_mode="Markdown", reply_markup=redeem_keyboard)

            else:
                bot.answer_callback_query(call.id, "Похоже, вы еще не подписались. Попробуйте снова.", show_alert=True)
        
        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "redeem_reward")
    def handle_redeem_reward(call: types.CallbackQuery):
        """Обрабатывает погашение награды и 'уничтожает' кнопку."""
        user_id = call.from_user.id

        if redeem_reward(user_id):
            final_text = "✅ Награда получена! Спасибо, что вы с нами. 😉"
            bot.edit_message_caption(caption=final_text, 
                                     chat_id=call.message.chat.id, 
                                     message_id=call.message.message_id, 
                                     reply_markup=None)
        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)
