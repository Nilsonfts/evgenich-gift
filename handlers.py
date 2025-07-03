# handlers.py
import logging
from telebot import types
from config import CHANNEL_ID
from database import user_exists, add_user, check_reward_status, grant_reward

def register_handlers(bot):
    """Регистрирует все обработчики сообщений и кнопок."""

    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username or "N/A"
        first_name = message.from_user.first_name

        # Добавляем пользователя в базу, если его там еще нет
        if not user_exists(user_id):
            add_user(user_id, username, first_name)
            logging.info(f"Новый пользователь: {first_name} (@{username}, {user_id})")

        # Проверяем, получал ли он уже награду
        if check_reward_status(user_id):
            bot.send_message(user_id, "Вы уже получали свой подарок. Спасибо, что вы с нами! 😉")
            return

        # Формируем приветственное сообщение
        welcome_text = (
            "Привет! 👋\n\n"
            "Подпишись на наш телеграм-канал и получи **фирменную настойку** в подарок!\n\n"
            "Нажми на кнопку ниже, когда подпишешься."
        )

        keyboard = types.InlineKeyboardMarkup()
        # Генерируем правильную ссылку на канал
        channel_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        subscribe_button = types.InlineKeyboardButton(text="➡️ Перейти к каналу", url=channel_url)
        check_button = types.InlineKeyboardButton(text="✅ Я подписался, проверить!", callback_data="check_subscription")
        keyboard.add(subscribe_button)
        keyboard.add(check_button)
        
        # Просто отправляем текст с кнопками
        bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        user_id = call.from_user.id

        if check_reward_status(user_id):
            bot.answer_callback_query(call.id)
            bot.edit_message_text("Вы уже получали свой подарок. Спасибо, что вы с нами! 😉",
                                     call.message.chat.id, call.message.message_id)
            return

        try:
            # Проверяем статус подписки
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

            if chat_member.status in ['member', 'administrator', 'creator']:
                # Пользователь подписан
                bot.answer_callback_query(call.id, "Отлично, подписка есть! ✅")
                grant_reward(user_id)

                coupon_text = (
                    "🎉 Поздравляем! 🎉\n\n"
                    "Ваш подарок - **фирменная настойка**.\n"
                    "Покажите это сообщение бармену, чтобы получить свой приз. Награда выдается один раз."
                )
                bot.send_message(user_id, coupon_text, parse_mode="Markdown")
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

            else:
                # Пользователь не подписан
                bot.answer_callback_query(call.id, "Похоже, вы еще не подписались. Попробуйте снова.", show_alert=True)

        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)
