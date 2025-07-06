# /handlers/callback_query.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from datetime import datetime, timedelta

# Импортируем конфиги, утилиты, тексты и клавиатуры
from config import CHANNEL_ID, THANK_YOU_STICKER_ID
import database  # <--- ГЛАВНОЕ ИЗМЕНЕНИЕ
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA
import texts
import keyboards

# Импортируем вспомогательную функцию из другого файла нашего хендлера
from .user_commands import issue_coupon

def register_callback_handlers(bot, scheduler, send_friend_bonus_func, request_feedback_func):
    """Регистрирует обработчики для всех inline-кнопок."""

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call: types.CallbackQuery):
        """
        Проверяет подписку на канал после нажатия кнопки.
        """
        user_id = call.from_user.id
        bot.answer_callback_query(call.id, text="Проверяю вашу подписку...")
        
        try:
            chat_member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except ApiTelegramException as e:
                    logging.warning(f"Не удалось удалить сообщение при проверке подписки (возможно, двойное нажатие): {e}")

                bot.send_message(user_id, texts.SUBSCRIPTION_SUCCESS_TEXT)
                issue_coupon(bot, user_id, call.message.chat.id)
            else:
                bot.answer_callback_query(call.id, texts.SUBSCRIPTION_FAIL_TEXT, show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Не удалось проверить подписку. Попробуйте позже.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "redeem_reward")
    def handle_redeem_reward(call: types.CallbackQuery):
        """
        Обрабатывает погашение купона на настойку.
        """
        user_id = call.from_user.id
        if database.update_status(user_id, 'redeemed'):
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except ApiTelegramException as e:
                logging.warning(f"Не удалось удалить сообщение при погашении купона (возможно, двойное нажатие): {e}")

            bot.send_message(call.message.chat.id, texts.REDEEM_SUCCESS_TEXT)
            
            try:
                bot.send_sticker(call.message.chat.id, THANK_YOU_STICKER_ID)
            except Exception as e:
                logging.error(f"Не удалось отправить прощальный стикер: {e}")
            
            bot.send_message(
                user_id, 
                texts.POST_REDEEM_INFO_TEXT,
                reply_markup=keyboards.get_main_menu_keyboard(user_id),
                parse_mode="Markdown"
            )

            # --- Отложенные задачи ---
            referrer_id = database.get_referrer_id_from_user(user_id)
            if referrer_id:
                friend_name = call.from_user.first_name or f"ID: {user_id}"
                # Бонус другу через 48 часов
                run_date_bonus = datetime.now() + timedelta(hours=48)
                scheduler.add_job(send_friend_bonus_func, 'date', run_date=run_date_bonus, args=[referrer_id, friend_name])
                logging.info(f"Запланирована отправка бонуса рефереру {referrer_id} на {run_date_bonus}.")

            # Запрос обратной связи через 24 часа
            run_date_feedback = datetime.now() + timedelta(hours=24)
            scheduler.add_job(request_feedback_func, 'date', run_date=run_date_feedback, args=[user_id])
            logging.info(f"Запланирован запрос ОС пользователю {user_id} на {run_date_feedback}.")

        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("feedback_"))
    def handle_feedback_rating(call: types.CallbackQuery):
        """Ловит оценку пользователя и сохраняет ее."""
        rating = call.data.split("_")[1]
        user_id = call.from_user.id
        bot.answer_callback_query(call.id, text="Спасибо за ваш отзыв!")
        bot.edit_message_text(f"Спасибо, товарищ! Ваша оценка: {'⭐'*int(rating)}", call.message.chat.id, call.message.message_id, reply_markup=None)

        database.log_ai_feedback(user_id, "feedback_after_visit", "N/A", rating)
        logging.info(f"Пользователь {user_id} оставил оценку: {rating}")

    # --- Обработчики для навигации по меню ---

    @bot.callback_query_handler(func=lambda call: call.data == "main_menu_choice")
    def callback_main_menu_choice(call: types.CallbackQuery):
        """Возвращает к главному выбору меню (Настойки/Кухня)."""
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                texts.MENU_PROMPT_TEXT,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.get_menu_choice_keyboard()
            )
        except ApiTelegramException as e:
            logging.warning(f"Не удалось вернуться к выбору меню: {e}")
            
    @bot.callback_query_handler(func=lambda call: call.data == "menu_nastoiki_main")
    def callback_menu_nastoiki_main(call: types.CallbackQuery):
        """Показывает главное меню с категориями настоек."""
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                texts.NASTOIKI_MENU_HEADER,
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=keyboards.get_nastoiki_categories_keyboard(), 
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
             logging.warning(f"Не удалось отредактировать сообщение меню (возможно, двойное нажатие): {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("menu_category_"))
    def callback_menu_category(call: types.CallbackQuery):
        """Показывает список настоек в выбранной категории."""
        bot.answer_callback_query(call.id)
        category_index = int(call.data.split("_")[2])
        category = MENU_DATA[category_index]
        
        text = f"**{category['title']}**\n_{category.get('category_narrative', '')}_\n\n"
        for item in category['items']:
            text += f"• **{item['name']}** — {item['price']}\n_{item['narrative_desc']}_\n\n"
        
        try:
            bot.edit_message_text(
                text, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=keyboards.get_nastoiki_items_keyboard(), 
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            logging.warning(f"Не удалось отредактировать сообщение категории (возможно, двойное нажатие): {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "menu_food_main")
    def callback_menu_food_main(call: types.CallbackQuery):
        """Показывает главное меню с категориями кухни."""
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                texts.FOOD_MENU_HEADER,
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=keyboards.get_food_categories_keyboard(), 
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            logging.warning(f"Не удалось отредактировать сообщение меню еды (возможно, двойное нажатие): {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("food_category_"))
    def callback_food_category(call: types.CallbackQuery):
        """Показывает список блюд в выбранной категории."""
        bot.answer_callback_query(call.id)
        category_name = call.data.replace("food_category_", "")
        category_items = FOOD_MENU_DATA.get(category_name, [])
        
        text = f"**{category_name}**\n\n"
        for item in category_items:
            text += f"• {item['name']} - **{item['price']}₽**\n"
        
        try:
            bot.edit_message_text(
                text, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=keyboards.get_food_items_keyboard(), 
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            logging.warning(f"Не удалось отредактировать сообщение категории еды (возможно, двойное нажатие): {e}")
