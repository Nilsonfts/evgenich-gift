# /handlers/callback_query.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from datetime import datetime, timedelta
import pytz # <--- ИЗМЕНЕНИЕ: Добавили библиотеку для часовых поясов

# Импортируем конфиги, утилиты, тексты и клавиатуры
from core.config import CHANNEL_ID, CHANNEL_ID_MSK, THANK_YOU_STICKER_ID, get_channel_id_for_user
import core.database as database
import texts
import keyboards

# Импортируем вспомогательную функцию из другого файла нашего хендлера
from .user_commands import issue_coupon, user_current_payload, get_channel_for_payload

# Импортируем систему уведомлений о рефералах
try:
    from utils.referral_notifications import send_immediate_referral_notification
except ImportError:
    logging.warning("Модуль уведомлений о рефералах не найден")
    send_immediate_referral_notification = None

def register_callback_handlers(bot, scheduler, send_friend_bonus_func, request_feedback_func):
    """Регистрирует обработчики для всех inline-кнопок."""

    # === ВЫБОР ГОРОДА (qr_bar → СПб или Москва) ===
    @bot.callback_query_handler(func=lambda call: call.data.startswith('city_select_'))
    def handle_city_select(call: types.CallbackQuery):
        """Обработка выбора города после заполнения профиля (qr_bar)."""
        try:
            bot.answer_callback_query(call.id)
            user_id = call.from_user.id

            if call.data == 'city_select_msk':
                new_payload = 'qr_bar_msk'
                city_name = 'Москва'
                source = 'QR-код на баре МСК'
                channel_link = 'https://t.me/evgenichmoscow'
            else:
                new_payload = 'qr_bar'
                city_name = 'Санкт-Петербург'
                source = 'QR-код на баре СПБ'
                channel_link = 'https://t.me/evgenichbarspb'

            # Обновляем payload для проверки подписки
            user_current_payload[user_id] = new_payload
            logging.info(f"🏙 Пользователь {user_id} выбрал город: {city_name} (payload={new_payload})")

            # Обновляем source в базе
            try:
                database.update_user_source(user_id, source)
                logging.info(f"✅ Source обновлён для {user_id}: {source}")
            except Exception as e:
                logging.warning(f"Не удалось обновить source: {e}")

            # Удаляем сообщение с выбором города
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass

            # Подтверждаем выбор и показываем подписку на правильный канал
            bot.send_message(user_id, f"📍 {city_name}! Отличный выбор! 🔥")

            subscribe_markup = types.InlineKeyboardMarkup(row_width=1)
            subscribe_markup.add(
                types.InlineKeyboardButton("➡️ Перейти к каналу", url=channel_link),
                types.InlineKeyboardButton("✅ Я подписался, проверить!", callback_data="check_subscription")
            )
            bot.send_message(
                user_id,
                texts.SUBSCRIBE_PROMPT_TEXT,
                reply_markup=subscribe_markup
            )

        except Exception as e:
            logging.error(f"❌ Ошибка выбора города: {e}", exc_info=True)
            try:
                bot.send_message(call.message.chat.id, "Произошла ошибка. Попробуй /start")
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda call: not (call.data.startswith('admin_') or call.data.startswith('boss_') or call.data.startswith('booking_') or call.data.startswith('source_') or call.data.startswith('bar_') or call.data.startswith('broadcast_') or call.data.startswith('newsletter_click_') or call.data.startswith('city_select_') or call.data in ['confirm_booking', 'cancel_booking']))
    def handle_all_callbacks(call: types.CallbackQuery):
        """Универсальный обработчик для неадминских callback-запросов."""
        logging.info(f"🔔 Получен callback: {call.data} от пользователя {call.from_user.id}")
        
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        
        try:
            # Передаем управление специфичным обработчикам
            if call.data == "check_subscription":
                handle_check_subscription(call)
            elif call.data == "redeem_reward":
                handle_redeem_reward(call)
            elif call.data.startswith("feedback_"):
                handle_feedback_rating(call)
            elif call.data.startswith("concept_"):
                callback_concept_choice(call)
            elif call.data.startswith("quiz_answer_"):
                callback_quiz_answer(call)
            elif call.data == "check_referral_rewards":
                handle_check_referral_rewards(call)
            elif call.data == "claim_reward":
                handle_claim_reward_callback(call)
            elif call.data == "show_referral_link":
                handle_show_referral_link(call)
            elif call.data == "show_referral_stats":
                handle_show_referral_stats(call)
            elif call.data == "start_booking":
                handle_start_booking_callback(call)
            else:
                logging.warning(f"Неизвестный callback: {call.data}")
        except Exception as e:
            logging.error(f"❌ Ошибка обработки callback {call.data}: {e}", exc_info=True)
            try:
                bot.send_message(call.message.chat.id, "⚠️ Произошла ошибка. Попробуй ещё раз!")
            except Exception:
                pass

    def handle_check_subscription(call: types.CallbackQuery):
        """
        Проверяет подписку на канал после нажатия кнопки.
        """
        user_id = call.from_user.id
        bot.answer_callback_query(call.id, text="Проверяю вашу подписку...")
        
        # ЖЁСТКАЯ ПРИВЯЗКА: используем сохранённый payload
        saved_payload = user_current_payload.get(user_id, '')
        channel_to_check = get_channel_for_payload(saved_payload)
        
        logging.info(f"🎯 Проверка подписки для {user_id}: payload='{saved_payload}', канал='{channel_to_check}'")
        
        try:
            chat_member = bot.get_chat_member(chat_id=channel_to_check, user_id=user_id)
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
            # 1. Удаляем сообщение с кнопкой (текст купона)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except ApiTelegramException as e:
                logging.warning(f"Не удалось удалить сообщение при погашении купона (возможно, двойное нажатие): {e}")

            # 2. Удаляем стикер-купон (отправлен прямо перед текстом купона)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id - 1)
            except Exception as e:
                logging.warning(f"Не удалось удалить стикер-купон: {e}")

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

            # --- Через 10 сек — предложение карты лояльности ---
            import threading
            def send_loyalty_offer():
                try:
                    loyalty_text = (
                        "🎁 Погоди, это ещё не всё!\n\n"
                        "Евгенич — щедрая душа. Ловишь *500 рублей на карту лояльности* 💰\n\n"
                        "Копи бонусы с каждого визита, трать на напитки и еду — "
                        "как свои, только приятнее 🥃\n\n"
                        "Жми 👇 и забирай!"
                    )
                    bot.send_message(
                        user_id,
                        loyalty_text,
                        reply_markup=keyboards.get_loyalty_keyboard(),
                        parse_mode="Markdown"
                    )
                    logging.info(f"💳 Отправлено предложение карты лояльности пользователю {user_id}")
                except Exception as e:
                    logging.error(f"Ошибка отправки предложения лояльности для {user_id}: {e}")

            timer = threading.Timer(10.0, send_loyalty_offer)
            timer.daemon = True
            timer.start()
            logging.info(f"💳 Запланировано предложение карты лояльности для {user_id} через 10 сек.")

            # --- Уведомления о рефералах ---
            referrer_id = database.get_referrer_id_from_user(user_id)
            if referrer_id:
                friend_name = call.from_user.first_name or call.from_user.username or f"ID{user_id}"
                
                # Отправляем немедленное уведомление рефереру
                if send_immediate_referral_notification:
                    try:
                        send_immediate_referral_notification(referrer_id, friend_name)
                        logging.info(f"Отправлено немедленное уведомление рефереру {referrer_id} о активации реферала {friend_name}")
                    except Exception as e:
                        logging.error(f"Ошибка отправки немедленного уведомления рефереру {referrer_id}: {e}")
                
                # Старая система (оставим как запасной вариант)
                run_date_bonus = datetime.now() + timedelta(hours=48)
                scheduler.add_job(send_friend_bonus_func, 'date', run_date=run_date_bonus, args=[referrer_id, friend_name])
                logging.info(f"Запланирована отправка бонуса рефереру {referrer_id} на {run_date_bonus} (резерв).")

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


    # --- Обработчики концепций чата ---
    def callback_concept_choice(call: types.CallbackQuery):
        """Обрабатывает выбор концепции для AI-ассистента."""
        bot.answer_callback_query(call.id)
        concept = call.data.replace("concept_", "")
        user_id = call.from_user.id
        
        # Принудительно устанавливаем концепцию "evgenich"
        database.update_user_concept(user_id, "evgenich")
        
        concept_names = {
            "evgenich": "ЕВГЕНИЧ (Классический)"
        }
        
        selected_name = concept_names.get("evgenich", "ЕВГЕНИЧ (Классический)")
        
        try:
            bot.edit_message_text(
                f"✅ Отлично! Активна концепция: **{selected_name}**\n\n"
                f"Я буду общаться с тобой в классическом стиле ЕВГЕНИЧ.",
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
            
            from modules.games import check_quiz_answer, save_game_result, QUIZ_QUESTIONS
            
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

    def handle_check_referral_rewards(call: types.CallbackQuery):
        """
        Проверяет и выдает награды за рефералов
        """
        user_id = call.from_user.id
        
        try:
            stats = database.get_referral_stats(user_id)
            
            if not stats or not stats['pending']:
                bot.answer_callback_query(call.id, "У вас нет ожидающих наград", show_alert=True)
                return
            
            rewards_given = 0
            messages = []
            
            for ref in stats['pending']:
                if ref['can_claim']:
                    # Проверяем право на награду
                    eligible, reason = database.check_referral_reward_eligibility(user_id, ref['user_id'])
                    
                    if eligible:
                        # Выдаем награду
                        success = database.mark_referral_rewarded(user_id, ref['user_id'])
                        
                        if success:
                            rewards_given += 1
                            name = ref['first_name'] or ref['username'] or f"ID{ref['user_id']}"
                            messages.append(f"✅ Награда за {name} получена!")
                    else:
                        name = ref['first_name'] or ref['username'] or f"ID{ref['user_id']}"
                        messages.append(f"❌ {name}: {reason}")
            
            # Формируем ответ
            if rewards_given > 0:
                response = f"🎉 Поздравляем! Вы получили {rewards_given} наград(ы)!\n\n"
                response += "\n".join(messages)
                
                # Генерируем уникальный код награды
                reward_code = f"REF{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Отправляем уведомление с наградой
                reward_message = f"🎁 *Ваша награда за приглашение друзей!*\n\n"
                reward_message += f"Вы получили {rewards_given} бесплатную(ые) настойку(и)!\n\n"
                reward_message += f"📱 Покажите этот код бармену:\n`{reward_code}`\n\n"
                reward_message += "✨ Спасибо за то, что приводите друзей к нам!"
                
                # Отправляем код награды отдельным сообщением
                bot.send_message(call.message.chat.id, reward_message, parse_mode="Markdown")
                
                # Логируем выдачу награды
                logging.info(f"Выдана реферальная награда пользователю {user_id}: {rewards_given} наград, код {reward_code}")
                
            else:
                response = "⏳ Пока нет доступных наград. Проверьте позже!\n\n"
                if messages:
                    response += "\n".join(messages)
            
            bot.answer_callback_query(call.id, f"Проверено! {rewards_given} наград получено." if rewards_given > 0 else "Наград пока нет.")
            
            # Обновляем сообщение с текущей статистикой
            from .user_commands import handle_friend_command
            handle_friend_command(call.message)
            
        except Exception as e:
            logging.error(f"Ошибка при проверке реферальных наград для {user_id}: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при проверке наград", show_alert=True)

    def handle_claim_reward_callback(call: types.CallbackQuery):
        """
        Обработчик кнопки 'Получить награду' из уведомления
        """
        try:
            user_id = call.from_user.id
            
            response_text = (
                "🥃 **Как получить награду:**\n\n"
                "1. Покажите код бармену\n"
                "2. Назовите: \"Реферальная награда\"\n"
                "3. Наслаждайтесь бесплатной настойкой!\n\n"
                "✨ Спасибо за приглашение друзей!"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("📍 Забронировать стол", callback_data="start_booking")
            )
            
            bot.edit_message_text(
                response_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            bot.answer_callback_query(call.id, "Покажите код бармену!")
            
        except Exception as e:
            logging.error(f"Ошибка при обработке получения награды: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка")

    def handle_show_referral_link(call: types.CallbackQuery):
        """
        Показывает реферальную ссылку
        """
        try:
            user_id = call.from_user.id
            from .user_commands import handle_friend_command
            
            # Создаем псевдо-сообщение для вызова существующего обработчика
            class PseudoMessage:
                def __init__(self, chat_id, user_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
                    self.from_user = type('obj', (object,), {'id': user_id})
            
            pseudo_msg = PseudoMessage(call.message.chat.id, user_id)
            handle_friend_command(pseudo_msg)
            
            bot.answer_callback_query(call.id, "Ваша реферальная ссылка обновлена")
            
        except Exception as e:
            logging.error(f"Ошибка показа реферальной ссылки: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка")

    def handle_show_referral_stats(call: types.CallbackQuery):
        """
        Показывает статистику рефералов
        """
        try:
            user_id = call.from_user.id
            from .user_commands import handle_friend_command
            
            # Создаем псевдо-сообщение для вызова существующего обработчика
            class PseudoMessage:
                def __init__(self, chat_id, user_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
                    self.from_user = type('obj', (object,), {'id': user_id})
            
            pseudo_msg = PseudoMessage(call.message.chat.id, user_id)
            handle_friend_command(pseudo_msg)
            
            bot.answer_callback_query(call.id, "Статистика обновлена")
            
        except Exception as e:
            logging.error(f"Ошибка показа статистики рефералов: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка")

    def handle_start_booking_callback(call: types.CallbackQuery):
        """
        Запускает процесс бронирования из уведомления
        """
        try:
            # Импортируем обработчик бронирования
            from .booking_flow import start_booking_flow
            
            # Запускаем поток бронирования
            start_booking_flow(bot, call.message, call.from_user.id)
            
            bot.answer_callback_query(call.id, "Начинаем бронирование!")
            
        except ImportError:
            # Если модуль бронирования не найден, показываем альтернативу
            response_text = (
                "📍 **Бронирование столика**\n\n"
                "Для бронирования свяжитесь с нами:\n"
                "📞 Телефон: +7 (XXX) XXX-XX-XX\n"
                "📱 Telegram: @evgenich_bar\n\n"
                "Или просто приходите - мы всегда рады гостям!"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            
            bot.edit_message_text(
                response_text,
                call.message.chat.id, 
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            bot.answer_callback_query(call.id, "Информация о бронировании")
            
        except Exception as e:
            logging.error(f"Ошибка запуска бронирования: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при бронировании")
            bot.send_message(user_id, "Произошла ошибка при обработке ответа. Попробуйте еще раз.")
