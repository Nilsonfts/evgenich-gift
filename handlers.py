# handlers.py
import logging
from telebot import types
from config import CHANNEL_ID
from g_sheets import get_reward_status, add_new_user, redeem_reward

def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        """Отправляет приветствие и одноразовую кнопку для новых пользователей."""
        user_id = message.from_user.id
        status = get_reward_status(user_id)
        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "С возвращением! Рады видеть вас снова. 😉")
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            get_gift_button = types.KeyboardButton("🎁 ПОЛУЧИТЬ НАСТОЙКУ")
            keyboard.add(get_gift_button)
            bot.send_message(message.chat.id, 
                             "Привет! 👋 Нажми на кнопку ниже, чтобы получить свой подарок.", 
                             reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == "🎁 ПОЛУЧИТЬ НАСТОЙКУ")
    def handle_get_gift_press(message: types.Message):
        """Обрабатывает нажатие на кнопку и УМНО проверяет подписку."""
        user_id = message.from_user.id
        status = get_reward_status(user_id)

        if status in ['issued', 'redeemed']:
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return
        
        # --- УМНАЯ ПРОВЕРКА ---
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            # Если пользователь УЖЕ подписан, сразу выдаем награду
            if chat_member.status in ['member', 'administrator', 'creator']:
                bot.send_message(user_id, "Вижу, ты уже наш подписчик! Спасибо тебе за это. ❤️")
                issue_coupon(bot, user_id, message.from_user.username, message.from_user.first_name)
                return
        except Exception as e:
            logging.error(f"Ошибка при предварительной проверке подписки для {user_id}: {e}")
            # Если произошла ошибка, просто продолжаем обычный флоу

        # --- ОБЫЧНЫЙ ФЛОУ ДЛЯ НОВЫХ ПОДПИСЧИКОВ ---
        welcome_text = (
            "Отлично! 👍\n\n"
            "Чтобы получить настойку, подпишись на наш телеграм-канал. Это займет всего секунду.\n\n"
            "Когда подпишешься — нажимай на кнопку «Я подписался» здесь же."
        )
        inline_keyboard = types.InlineKeyboardMarkup(row_width=1)
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        subscribe_button = types.InlineKeyboardButton(text="➡️ Перейти к каналу", url=channel_url)
        check_button = types.InlineKeyboardButton(text="✅ Я подписался, проверить!", callback_data="check_subscription")
        inline_keyboard.add(subscribe_button, check_button)
        
        try:
            with open('hello.png', 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")
        except FileNotFoundError:
            bot.send_message(message.chat.id, welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        """Проверяет подписку для тех, кто только что подписался."""
        user_id = call.from_user.id
        
        # Дополнительное уведомление для пользователя
        bot.answer_callback_query(call.id, text="Проверяю вашу подписку...")

        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                # Убираем кнопки "Перейти/Проверить"
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                issue_coupon(bot, user_id, call.from_user.username, call.from_user.first_name)
            else:
                bot.answer_callback_query(call.id, "Похоже, вы еще не подписались. Попробуйте снова.", show_alert=True)
        
        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "redeem_reward")
    def handle_redeem_reward(call: types.CallbackQuery):
        """Обрабатывает погашение награды."""
        user_id = call.from_user.id
        if redeem_reward(user_id):
            final_text = "✅ Награда получена! Спасибо, что вы с нами. 😉"
            bot.edit_message_caption(caption=final_text, 
                                     chat_id=call.message.chat.id, 
                                     message_id=call.message.message_id, 
                                     reply_markup=None)
        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)

# Вспомогательная функция, чтобы не дублировать код выдачи купона
def issue_coupon(bot, user_id, username, first_name):
    """Выдает купон пользователю."""
    status = get_reward_status(user_id)
    if status in ['issued', 'redeemed']:
        # Эта проверка нужна, чтобы избежать двойной выдачи из-за быстрых нажатий
        return

    add_new_user(user_id, username or "N/A", first_name)
    
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
    
    try:
        with open('nastoyka.png', 'rb') as photo:
            bot.send_photo(user_id, photo, caption=coupon_text, parse_mode="Markdown", reply_markup=redeem_keyboard)
    except FileNotFoundError:
        bot.send_message(user_id, coupon_text, parse_mode="Markdown", reply_markup=redeem_keyboard)
