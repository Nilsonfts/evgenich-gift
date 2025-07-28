# /handlers/callback_query.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from datetime import datetime, timedelta
import pytz # <--- ИЗМЕНЕНИЕ: Добавили библиотеку для часовых поясов

# Импортируем конфиги, утилиты, тексты и клавиатуры
from config import CHANNEL_ID, THANK_YOU_STICKER_ID
import database
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA
import texts
import keyboards

# Импортируем вспомогательную функцию из другого файла нашего хендлера
from .user_commands import issue_coupon

def register_callback_handlers(bot, scheduler, send_friend_bonus_func, request_feedback_func):
    """Регистрирует обработчики для всех inline-кнопок."""

    @bot.callback_query_handler(func=lambda call: not (call.data.startswith('admin_') or call.data.startswith('boss_') or call.data.startswith('booking_')))
    def handle_all_callbacks(call: types.CallbackQuery):
        """Универсальный обработчик для неадминских callback-запросов."""
        logging.info(f"Получен callback: {call.data} от пользователя {call.from_user.id}")
        
        # Передаем управление специфичным обработчикам
        if call.data == "check_subscription":
            handle_check_subscription(call)
        elif call.data == "redeem_reward":
            handle_redeem_reward(call)
        elif call.data.startswith("feedback_"):
            handle_feedback_rating(call)
        elif call.data == "main_menu_choice":
            callback_main_menu_choice(call)
        elif call.data == "menu_nastoiki_main":
            callback_menu_nastoiki_main(call)
        elif call.data.startswith("menu_category_"):
            callback_menu_category(call)
        elif call.data == "menu_food_main":
            callback_menu_food_main(call)
        elif call.data.startswith("food_category_"):
            callback_food_category(call)
        elif call.data.startswith("concept_"):
            callback_concept_choice(call)
        elif call.data.startswith("quiz_answer_"):
            callback_quiz_answer(call)
        else:
            logging.warning(f"Неизвестный callback: {call.data}")
            bot.answer_callback_query(call.id, "Неизвестная команда")

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

    def handle_redeem_reward(call: types.CallbackQuery):
        """
        Обрабатывает погашение купона на настойку.
        """
        user_id = call.from_user.id
        # --- НАЧАЛО ИЗМЕНЕНИЙ ---
        if database.update_status(user_id, 'redeemed'):
            # 1. Удаляем кнопку
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except ApiTelegramException as e:
                logging.warning(f"Не удалось удалить сообщение при погашении купона (возможно, двойное нажатие): {e}")

            # 2. Получаем и форматируем текущее время
            tz_moscow = pytz.timezone('Europe/Moscow')
            redeem_time = datetime.now(tz_moscow).strftime('%d.%m.%Y в %H:%M')
            
            # 3. Создаем новое сообщение с датой и временем
            final_text = (
                f"✅ Ну, за знакомство!\n\n"
                f"КУПОН ПОГАШЕН: {redeem_time.upper()}\n\n" # Добавляем время капсом
                f"Как гласит древняя мудрость: между первой и второй культурный перерывчик минут пять. Приходи, продолжим!"
            )
            
            # 4. Отправляем новое, отформатированное сообщение
            bot.send_message(call.message.chat.id, final_text)
            # --- КОНЕЦ ИЗМЕНЕНИЙ ---
            
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
                run_date_bonus = datetime.now() + timedelta(hours=48)
                scheduler.add_job(send_friend_bonus_func, 'date', run_date=run_date_bonus, args=[referrer_id, friend_name])
                logging.info(f"Запланирована отправка бонуса рефереру {referrer_id} на {run_date_bonus}.")

            run_date_feedback = datetime.now() + timedelta(hours=24)
            scheduler.add_job(request_feedback_func, 'date', run_date=run_date_feedback, args=[user_id])
            logging.info(f"Запланирован запрос ОС пользователю {user_id} на {run_date_feedback}.")

        else:
            bot.answer_callback_query(call.id, "Эта награда уже была использована.", show_alert=True)

    def handle_feedback_rating(call: types.CallbackQuery):
        """Ловит оценку пользователя и сохраняет ее."""
        rating = call.data.split("_")[1]
        user_id = call.from_user.id
        bot.answer_callback_query(call.id, text="Спасибо за ваш отзыв!")
        bot.edit_message_text(f"Спасибо, товарищ! Ваша оценка: {'⭐'*int(rating)}", call.message.chat.id, call.message.message_id, reply_markup=None)

        # Предполагаем, что у вас есть функция для логирования
        # database.log_ai_feedback(user_id, "feedback_after_visit", "N/A", rating)
        logging.info(f"Пользователь {user_id} оставил оценку: {rating}")

    # --- Обработчики для навигации по меню ---

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

    # --- Обработчики концепций чата ---
    def callback_concept_choice(call: types.CallbackQuery):
        """Обрабатывает выбор концепции для AI-ассистента."""
        bot.answer_callback_query(call.id)
        concept = call.data.replace("concept_", "")
        user_id = call.from_user.id
        
        # Сохраняем выбранную концепцию в базе данных
        database.update_user_concept(user_id, concept)
        
        concept_names = {
            "rvv": "РВВ (Руки Вверх Винтаж)",
            "evgenich": "ЕВГЕНИЧ (Классический)",
            "nebar": "НЕБАР (Необычный барный стиль)",
            "spletni": "СПЛЕТНИ (Дружеская болтовня)",
            "orbita": "ОРБИТА (Космический стиль)"
        }
        
        selected_name = concept_names.get(concept, concept.upper())
        
        try:
            bot.edit_message_text(
                f"✅ Отлично! Выбрана концепция: **{selected_name}**\n\n"
                f"Теперь я буду общаться с тобой в этом стиле. "
                f"Можешь в любой момент изменить концепцию через команду /concept",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            logging.warning(f"Не удалось отредактировать сообщение выбора концепции: {e}")

    def callback_quiz_answer(call: types.CallbackQuery):
        """Обрабатывает ответы на вопросы викторины."""
        user_id = call.from_user.id
        
        try:
            # Парсим данные callback: quiz_answer_questionIndex_answerIndex
            parts = call.data.split("_")
            if len(parts) != 4:
                bot.answer_callback_query(call.id, "Ошибка данных")
                return
                
            question_index = int(parts[2])
            user_answer = int(parts[3])
            
            from games import check_quiz_answer, save_game_result, QUIZ_QUESTIONS
            
            # Проверяем ответ
            result = check_quiz_answer(question_index, user_answer)
            
            if "error" in result:
                bot.answer_callback_query(call.id, result["error"])
                return
            
            # Сохраняем результат в базу
            save_game_result(user_id, "quiz", result)
            
            # Формируем ответ
            if result["is_correct"]:
                response = f"✅ **Правильно!**\n\n{result['explanation']}\n\n{result['reward']}"
                bot.answer_callback_query(call.id, "Правильно! 🎉", show_alert=True)
            else:
                response = f"❌ **Неверно!**\n\nПравильный ответ: {result['correct_answer']}\n\n{result['explanation']}\n\n{result['reward']}"
                bot.answer_callback_query(call.id, "Неверно 😔", show_alert=True)
            
            # Обновляем сообщение с результатом
            bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            
        except Exception as e:
            logging.error(f"Ошибка при обработке ответа викторины для пользователя {user_id}: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка")
            bot.send_message(user_id, "Произошла ошибка при обработке ответа. Попробуйте еще раз.")
