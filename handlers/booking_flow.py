# /handlers/booking_flow.py

import logging
import re
from telebot import types
from telebot.apihelper import ApiTelegramException
from tinydb import TinyDB, Query

# Импортируем конфиги, тексты и клавиатуры
from core.config import BOOKING_NOTIFICATIONS_CHAT_ID, BOOKING_NOTIFICATIONS_CHAT_ID_MSK, REPORT_CHAT_ID
from core.admin_config import get_bars, get_bar_by_callback
import texts
import keyboards
import core.settings_manager as settings_manager # Наш новый менеджер настроек

# Импортируем функцию экспорта в соцсети
from utils.social_bookings_export import (
    export_social_booking_to_sheets, 
    export_guest_booking_to_sheets,
    parse_booking_date, 
    parse_booking_time
)

# Инициализация базы данных для бронирований
db = TinyDB('booking_data.json')
User = Query()

# --- Экспортируемая функция для запуска бронирования извне ---

def start_booking_flow(bot, message, user_id):
    """Запускает процесс бронирования. Может вызываться из других модулей."""
    db.upsert({'user_id': user_id, 'step': 'name', 'data': {}}, User.user_id == user_id)
    bot.send_message(message.chat.id, texts.BOOKING_START_PROMPT, parse_mode="Markdown")

# --- Регистрация обработчиков ---

def register_booking_handlers(bot):
    """
    Регистрирует полный цикл обработчиков для пошагового бронирования стола.
    """

    def _start_booking_process(chat_id, user_id):
        """Начинает или перезапускает процесс бронирования для пользователя."""
        db.upsert({'user_id': user_id, 'step': 'name', 'data': {}}, User.user_id == user_id)
        bot.send_message(chat_id, texts.BOOKING_START_PROMPT, parse_mode="Markdown")

    def _cancel_booking(message):
        """Отменяет процесс бронирования и удаляет данные пользователя из БД."""
        user_id = message.from_user.id
        if db.contains(User.user_id == user_id):
            db.remove(User.user_id == user_id)
            bot.send_message(
                user_id,
                texts.BOOKING_CANCELLED_TEXT,
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
        else:
            bot.reply_to(message, "Нет активного действия для отмены.")

    # --- Обработчики команд ---
    @bot.message_handler(commands=['cancel'])
    def handle_cancel_command(message: types.Message):
        """Обрабатывает команду /cancel, чтобы выйти из любого состояния."""
        _cancel_booking(message)

    @bot.message_handler(commands=['book'])
    @bot.message_handler(func=lambda message: message.text == "📍 Забронировать стол")
    def handle_booking_entry(message: types.Message):
        # В групповых чатах бронирование только для боссов/админов
        if message.chat.type != 'private':
            from core.config import ALL_ADMINS
            if message.from_user.id not in ALL_ADMINS:
                bot.reply_to(message, "🔒 Для бронирования используйте закрепленную кнопку в чате или напишите мне в личку: @evgenichspbbot")
                return
        
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, texts.BOOKING_IN_PROGRESS_TEXT)
            return

        logging.info(f"Пользователь {message.from_user.id} нажал 'Забронировать стол'.")
        bot.send_message(
            message.chat.id,
            texts.BOOKING_PROMPT_TEXT,
            reply_markup=keyboards.get_booking_options_keyboard()
        )

    @bot.message_handler(func=lambda message: message.text == "📨 Отправить БРОНЬ")
    def handle_admin_booking_entry(message: types.Message):
        from core.config import ALL_BOOKING_STAFF
        if message.from_user.id not in ALL_BOOKING_STAFF:
            bot.reply_to(message, "❌ У вас нет доступа к созданию броней.")
            return
            
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, "Уже создаётся бронь. Завершите текущую или /cancel")
            return

        logging.info(f"Админ {message.from_user.id} начал создание брони.")
        db.upsert({'user_id': message.from_user.id, 'step': 'admin_name', 'data': {'is_admin_booking': True}}, User.user_id == message.from_user.id)
        bot.send_message(message.chat.id, texts.ADMIN_BOOKING_START)

    # --- Обработчики нажатий на кнопки ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("source_"))
    def handle_traffic_source_callback(call: types.CallbackQuery):
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)
        
        logging.info(f"📊 Админ {user_id} выбрал источник: {call.data}")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except ApiTelegramException:
            pass

        user_entry = db.get(User.user_id == user_id)
        if not user_entry:
            logging.error(f"❌ Запись о бронировании не найдена для администратора {user_id}")
            bot.send_message(call.message.chat.id, "❌ Ошибка! Начни заново: /send_booking")
            return

        current_data = user_entry.get('data', {})
        current_data['source'] = call.data
        
        logging.info(f"✅ Источник сохранён: {current_data.get('source')}")
        
        # Переходим к следующему шагу (выбор бара)
        db.update({'step': 'bar', 'data': current_data}, User.user_id == user_id)
        
        if current_data.get('is_admin_booking'):
            bot.send_message(call.message.chat.id, texts.ADMIN_BOOKING_BAR, reply_markup=keyboards.get_bar_selection_keyboard())
        else:
            bot.send_message(call.message.chat.id, texts.BOOKING_ASK_BAR, reply_markup=keyboards.get_bar_selection_keyboard())

    @bot.callback_query_handler(func=lambda call: call.data.startswith("bar_"))
    def handle_bar_selection_callback(call: types.CallbackQuery):
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)
        
        logging.info(f"🏠 Пользователь {user_id} выбрал бар: {call.data}")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except ApiTelegramException:
            pass

        user_entry = db.get(User.user_id == user_id)
        if not user_entry:
            logging.error(f"❌ Запись о бронировании не найдена для пользователя {user_id}")
            bot.send_message(call.message.chat.id, "❌ Ошибка! Запись о бронировании потеряна. Начни заново: /book")
            return

        current_data = user_entry.get('data', {})
        
        # Получаем информацию о баре из админ-панели
        bar_info = get_bar_by_callback(call.data)
        if bar_info:
            current_data['bar'] = call.data
            current_data['amo_tag'] = bar_info.get('code', '')
            logging.info(f"✅ Сохраняю выбор бара: bar={call.data}, amo_tag={current_data.get('amo_tag')}, name={bar_info.get('name')}")
        else:
            # Фоллбэк на старую систему, если бар не найден
            bar_mapping = {
                'bar_nevsky': 'ЕВГ_СПБ',
                'bar_rubinstein': 'ЕВГ_СПБ_РУБ',
                'bar_pyatnitskaya': 'ЕВГ_МСК_ПЯТ',
                'bar_tsvetnoj': 'ЕВГ_МСК_ЦВЕТ'
            }
            current_data['bar'] = call.data
            current_data['amo_tag'] = bar_mapping.get(call.data, '')
            logging.warning(f"⚠️ Бар {call.data} не найден в админ-панели, использую старый маппинг")
        
        logging.info(f"✅ Сохраняю выбор бара: bar={current_data.get('bar')}, amo_tag={current_data.get('amo_tag')}")
        
        # Переходим к подтверждению
        db.update({'step': 'confirmation', 'data': current_data}, User.user_id == user_id)
        confirmation_text = texts.get_booking_confirmation_text(current_data)
        bot.send_message(
            call.message.chat.id,
            confirmation_text,
            reply_markup=keyboards.get_booking_confirmation_keyboard()
        )
        
        logging.info(f"✅ Подтверждение отправлено пользователю {user_id}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("booking_"))
    def handle_booking_option_callback(call: types.CallbackQuery):
        logging.info(f"📍 Получен booking callback: {call.data} от пользователя {call.from_user.id}")
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"Ошибка answer_callback_query: {e}")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        try:
            if call.data == "booking_phone":
                bot.send_message(call.message.chat.id, texts.BOOKING_PHONE_TEXT)
            elif call.data == "booking_site":
                bot.send_message(call.message.chat.id, texts.BOOKING_SITE_TEXT)
            elif call.data == "booking_secret":
                bot.send_message(call.message.chat.id, texts.BOOKING_SECRET_CHAT_TEXT, reply_markup=keyboards.get_secret_chat_keyboard())
            elif call.data == "booking_bot":
                # Начинаем бронирование для гостя
                db.upsert({'user_id': call.from_user.id, 'step': 'name', 'data': {'is_guest_booking': True}}, User.user_id == call.from_user.id)
                bot.send_message(
                    call.message.chat.id, 
                    "🌟 Отлично! Давайте забронируем для вас столик.\n\n"
                    "Как вас зовут?",
                    reply_markup=keyboards.get_cancel_booking_keyboard()
                )
            logging.info(f"✅ Booking callback {call.data} обработан успешно")
        except Exception as e:
            logging.error(f"❌ Ошибка обработки booking callback {call.data}: {e}", exc_info=True)
            try:
                bot.send_message(call.message.chat.id, "⚠️ Произошла ошибка. Попробуйте ещё раз нажать 📍 Забронировать стол")
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_booking", "cancel_booking"])
    def handle_booking_confirmation_callback(call: types.CallbackQuery):
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except ApiTelegramException:
            pass

        user_entry = db.get(User.user_id == user_id)
        if not user_entry:
            return

        if call.data == "confirm_booking":
            booking_data = user_entry.get('data', {})
            is_admin_booking = booking_data.get('is_admin_booking', False)
            
            # Если это админская бронировка, экспортируем в таблицу соцсетей
            if is_admin_booking:
                try:
                    export_success = export_social_booking_to_sheets(booking_data, user_id)
                    if export_success:
                        logging.info(f"Админская заявка успешно экспортирована в Google Sheets. Админ: {user_id}")
                    else:
                        logging.error(f"Ошибка экспорта админской заявки в Google Sheets. Админ: {user_id}")
                except Exception as e:
                    logging.error(f"Исключение при экспорте админской заявки: {e}")
            else:
                # Если это гостевое бронирование, экспортируем в таблицу без источника
                try:
                    export_success = export_guest_booking_to_sheets(booking_data, user_id)
                    if export_success:
                        logging.info(f"Гостевая заявка успешно экспортирована в Google Sheets. Гость: {booking_data.get('name', '')}")
                    else:
                        logging.error(f"Ошибка экспорта гостевой заявки в Google Sheets. Гость: {booking_data.get('name', '')}")
                except Exception as e:
                    logging.error(f"Исключение при экспорте гостевой заявки: {e}")
            
            # Создаем отчет с указанием создателя брони
            report_text = texts.get_booking_report_text(booking_data, user_id)

            promo = settings_manager.get_setting("promotions.group_bonus")
            try:
                # Пытаемся преобразовать количество гостей в число
                num_guests = int(booking_data.get('guests', '0').strip())
                if promo and promo.get('is_active') and num_guests >= promo.get('min_guests', 4):
                    bonus_text_for_report = promo.get('bonus_text', 'графин')
                    # Добавляем информацию о бонусе
                    report_text += f"\n\n🚨 <b>ВНИМАНИЕ:</b> Гость идет с бонусом '<b>{bonus_text_for_report}</b>'!"
                    bot.send_message(user_id, texts.get_group_bonus_text(bonus_text_for_report), parse_mode="Markdown")
            except (ValueError, TypeError) as e:
                # Эта ошибка теперь будет возникать гораздо реже, но оставим логирование на всякий случай
                logging.warning(f"Не удалось определить кол-во гостей для бонуса (ошибка при конвертации): {e}")
                pass

            # Отправляем отчет с поддержкой HTML-разметки
            # Определяем куда отправлять в зависимости от бара
            selected_bar = booking_data.get('bar', '')
            if selected_bar in ('bar_pyatnitskaya', 'bar_tsvetnoj'):
                notification_chat_id = BOOKING_NOTIFICATIONS_CHAT_ID_MSK
                logging.info(f"🇷🇺 Московское бронирование - отправляю в чат МСК {notification_chat_id}")
            else:
                notification_chat_id = BOOKING_NOTIFICATIONS_CHAT_ID
                logging.info(f"🏛️ Питерское бронирование - отправляю в чат СПБ {notification_chat_id}")
            
            try:
                bot.send_message(notification_chat_id, report_text, parse_mode="HTML")
                logging.info(f"Уведомление о бронировании успешно отправлено в чат {notification_chat_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления в чат {notification_chat_id}: {e}")
                # Fallback - отправляем в старый чат если новый недоступен
                try:
                    bot.send_message(REPORT_CHAT_ID, report_text, parse_mode="HTML")
                    logging.info(f"Уведомление отправлено в резервный чат {REPORT_CHAT_ID}")
                except Exception as fallback_error:
                    logging.error(f"Ошибка отправки в резервный чат: {fallback_error}")
            bot.send_message(
                user_id,
                texts.BOOKING_CONFIRMATION_SUCCESS,
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            db.remove(User.user_id == user_id)

            # Предлагаем карту лояльности после успешного бронирования
            try:
                bot.send_message(
                    user_id,
                    "🎉 <b>Лови ништяк от Евгенича!</b>\n\n"
                    "Дарю тебе <b>500 подарочных бонусов</b> 💰 на карту лояльности!\n\n"
                    "Копи бонусы с каждого заказа и трать на любимые напитки 🥃 и любимые блюда 🍽\n\n"
                    "Жми кнопку 👇 и забирай свой подарок!",
                    parse_mode="HTML",
                    reply_markup=keyboards.get_loyalty_keyboard()
                )
                logging.info(f"🎁 Предложена карта лояльности после бронирования для пользователя {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки предложения карты лояльности: {e}")

        elif call.data == "cancel_booking":
            _start_booking_process(call.message.chat.id, user_id)

    # --- УЛУЧШЕННЫЙ ОБРАБОТЧИК ВСЕХ ШАГОВ БРОНИРОВАНИЯ ---
    @bot.message_handler(func=lambda message: db.contains(User.user_id == message.from_user.id) and message.chat.type == 'private', content_types=['text'])
    def process_booking_step(message: types.Message):
        user_id = message.from_user.id
        user_entry = db.get(User.user_id == user_id)
        
        if not user_entry or not user_entry.get('step'):
            return
        
        # Игнорируем команды и кнопки - пусть их обрабатывают другие обработчики
        if message.text.startswith('/') or message.text in ['🎁 Карта лояльности', '⭐ Оставить отзыв', '🗣 Спроси у Евгенича', '🥃 Получить настойку по талону', '📍 Забронировать стол', '👑 Админка', '📨 Отправить БРОНЬ']:
            return

        step = user_entry.get('step')
        current_data = user_entry.get('data', {})
        is_admin_booking = current_data.get('is_admin_booking', False)

        # Проверяем ввод на шаге 'телефон' - ТОЛЬКО ЦИФРЫ!
        if step == 'phone':
            # Убираем все кроме цифр и +
            phone_digits = ''.join(filter(lambda x: x.isdigit() or x == '+', message.text))
            
            # Проверяем что осталось минимум 10 цифр
            digit_count = len([c for c in phone_digits if c.isdigit()])
            
            if digit_count < 10:
                bot.send_message(
                    message.chat.id, 
                    "❌ Это не похоже на номер телефона, товарищ!\n\n"
                    "📱 Напиши только номер телефона (минимум 10 цифр).\n"
                    "Примеры:\n"
                    "• 89991234567\n"
                    "• +79991234567\n"
                    "• 8 (999) 123-45-67", 
                    reply_markup=keyboards.get_cancel_booking_keyboard()
                )
                return
        
        # Проверяем ввод на шаге 'гости' - ТОЛЬКО ЦИФРЫ!
        if step == 'guests':
            # Проверяем что введено число
            if not message.text.strip().isdigit():
                bot.send_message(
                    message.chat.id, 
                    "❌ Товарищ, укажи количество гостей цифрой!\n\n"
                    "👥 Например: 2, 4, 6, 10", 
                    reply_markup=keyboards.get_cancel_booking_keyboard()
                )
                return
            
            # Проверяем что число разумное (от 1 до 50)
            guests_count = int(message.text.strip())
            if guests_count < 1 or guests_count > 50:
                bot.send_message(
                    message.chat.id,
                    "❌ Количество гостей должно быть от 1 до 50 человек.\n\n"
                    "👥 Для больших компаний позвони нам: +7(812)237-59-50",
                    reply_markup=keyboards.get_cancel_booking_keyboard()
                )
                return
        
        # Проверяем если пользователь на шаге 'bar' - ему нужно нажать на кнопку!
        if step == 'bar':
            bot.send_message(message.chat.id, "Пожалуйста, выбери бар кнопкой выше 👆", 
                           reply_markup=keyboards.get_bar_selection_keyboard())
            return

        # Обрабатываем дату - парсим и проверяем
        if step == 'date':
            parsed_date = parse_booking_date(message.text)
            
            # Проверяем что дата была успешно распознана (формат DD.MM.YYYY)
            date_pattern = r'^\d{2}\.\d{2}\.\d{4}$'
            if not re.match(date_pattern, parsed_date):
                bot.send_message(
                    message.chat.id,
                    "❌ Не могу понять дату, товарищ!\n\n"
                    "📅 Напиши дату в одном из форматов:\n"
                    "• Завтра\n"
                    "• В субботу\n"
                    "• 15 января\n"
                    "• 15.01\n"
                    "• 15.01.2026",
                    reply_markup=keyboards.get_cancel_booking_keyboard()
                )
                return
            
            current_data[step] = parsed_date
            # Показываем распознанную дату пользователю
            if parsed_date != message.text:
                bot.send_message(message.chat.id, f"✅ Понял, дата: {parsed_date}")
                
        # Обрабатываем время - парсим в формат ЧЧ:ММ  
        elif step == 'time':
            parsed_time = parse_booking_time(message.text)
            
            # Проверяем что время было успешно распознано (формат ЧЧ:ММ)
            time_pattern = r'^\d{2}:\d{2}$'
            if not re.match(time_pattern, parsed_time):
                bot.send_message(
                    message.chat.id,
                    "❌ Не могу понять время, товарищ!\n\n"
                    "⏰ Напиши время в одном из форматов:\n"
                    "• 19:30\n"
                    "• 19.30\n"
                    "• 19 30\n"
                    "• 1930",
                    reply_markup=keyboards.get_cancel_booking_keyboard()
                )
                return
            
            current_data[step] = parsed_time
            # Показываем распознанное время пользователю
            if parsed_time != message.text:
                bot.send_message(message.chat.id, f"✅ Понял, время: {parsed_time}")
        # Обрабатываем телефон - сохраняем только цифры
        elif step == 'phone':
            phone_clean = ''.join(filter(lambda x: x.isdigit() or x == '+', message.text))
            current_data[step] = phone_clean
            # Показываем очищенный номер
            if phone_clean != message.text:
                bot.send_message(message.chat.id, f"✅ Понял, телефон: {phone_clean}")
        else:
            # Сохраняем ответ пользователя в его данные как есть
            current_data[step] = message.text

        # Словарь-маршрутизатор по шагам для обычного бронирования
        user_prompts = {
            'name': {'next_step': 'phone', 'prompt': texts.BOOKING_ASK_PHONE, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'phone': {'next_step': 'date', 'prompt': texts.BOOKING_ASK_DATE, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'date': {'next_step': 'time', 'prompt': texts.BOOKING_ASK_TIME, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'time': {'next_step': 'guests', 'prompt': texts.BOOKING_ASK_GUESTS, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'guests': {'next_step': 'bar', 'prompt': texts.BOOKING_ASK_BAR, 'keyboard': keyboards.get_bar_selection_keyboard()},
        }

        # Словарь-маршрутизатор для админского бронирования
        admin_prompts = {
            'admin_name': {'next_step': 'phone', 'prompt': texts.ADMIN_BOOKING_PHONE, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'phone': {'next_step': 'date', 'prompt': texts.ADMIN_BOOKING_DATE, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'date': {'next_step': 'time', 'prompt': texts.ADMIN_BOOKING_TIME, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'time': {'next_step': 'guests', 'prompt': texts.ADMIN_BOOKING_GUESTS, 'keyboard': keyboards.get_cancel_booking_keyboard()},
            'guests': {'next_step': 'source', 'prompt': texts.ADMIN_BOOKING_SOURCE, 'keyboard': keyboards.get_traffic_source_keyboard()},
        }

        # Выбираем нужный маршрутизатор
        prompts = admin_prompts if is_admin_booking else user_prompts

        if step in prompts:
            # Для админского бронирования переименовываем admin_name в name в данных
            if step == 'admin_name':
                current_data['name'] = current_data.pop('admin_name')
                
            # Если это не последний шаг, переводим на следующий
            next_step_info = prompts[step]
            db.update({'step': next_step_info['next_step'], 'data': current_data}, User.user_id == user_id)
            
            # Отправляем сообщение с клавиатурой если есть
            if 'keyboard' in next_step_info:
                bot.send_message(message.chat.id, next_step_info['prompt'], reply_markup=next_step_info['keyboard'])
            else:
                bot.send_message(message.chat.id, next_step_info['prompt'])
