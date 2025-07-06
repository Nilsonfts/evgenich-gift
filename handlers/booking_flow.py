# /handlers/booking_flow.py

import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from tinydb import TinyDB, Query

# Импортируем конфиги, тексты и клавиатуры
from config import REPORT_CHAT_ID
import texts
import keyboards
import settings_manager # Наш новый менеджер настроек

# Инициализация базы данных для бронирований
db = TinyDB('booking_data.json')
User = Query()

# --- Регистрация обработчиков ---

def register_booking_handlers(bot):
    """
    Регистрирует полный цикл обработчиков для пошагового бронирования стола.
    """

    def _start_booking_process(chat_id, user_id):
        """Начинает или перезапускает процесс бронирования для пользователя."""
        # Создаем или обновляем запись в БД, указывая, что пользователь на шаге 'name'
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
            # Если пользователь не был в процессе бронирования
            bot.reply_to(message, "Нет активного действия для отмены.")

    # --- Обработчики команд ---
    @bot.message_handler(commands=['cancel'])
    def handle_cancel_command(message: types.Message):
        """Обрабатывает команду /cancel, чтобы выйти из любого состояния."""
        _cancel_booking(message)

    @bot.message_handler(commands=['book'])
    @bot.message_handler(func=lambda message: message.text == "📍 Забронировать стол")
    def handle_booking_entry(message: types.Message):
        """
        Точка входа в бронирование. Показывает начальные варианты.
        """
        # Проверяем, не находится ли пользователь уже в процессе бронирования
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, texts.BOOKING_IN_PROGRESS_TEXT)
            return

        logging.info(f"Пользователь {message.from_user.id} нажал 'Забронировать стол'.")
        bot.send_message(
            message.chat.id,
            texts.BOOKING_PROMPT_TEXT,
            reply_markup=keyboards.get_booking_options_keyboard()
        )

    # --- Обработчики нажатий на кнопки ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("booking_"))
    def handle_booking_option_callback(call: types.CallbackQuery):
        """
        Обрабатывает выбор пользователя (позвонить, сайт, бот).
        """
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except ApiTelegramException:
            pass # Игнорируем ошибку, если сообщение уже удалено

        if call.data == "booking_phone":
            bot.send_message(call.message.chat.id, texts.BOOKING_PHONE_TEXT, parse_mode="Markdown")
        elif call.data == "booking_site":
            bot.send_message(call.message.chat.id, texts.BOOKING_SITE_TEXT)
        elif call.data == "booking_secret":
            bot.send_message(call.message.chat.id, texts.BOOKING_SECRET_CHAT_TEXT, reply_markup=keyboards.get_secret_chat_keyboard())
        elif call.data == "booking_bot":
            _start_booking_process(call.message.chat.id, call.from_user.id)

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_booking", "cancel_booking"])
    def handle_booking_confirmation_callback(call: types.CallbackQuery):
        """
        Обрабатывает финальное решение пользователя и добавляет бонус для компании, если нужно.
        """
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
            report_text = texts.get_booking_report_text(booking_data)

            # --- Логика бонуса для компании ---
            promo = settings_manager.get_setting("promotions.group_bonus")
            try:
                # Пытаемся преобразовать количество гостей в число
                num_guests = int(booking_data.get('guests', '0').strip())
                if promo and promo.get('is_active') and num_guests >= promo.get('min_guests', 4):
                    # Добавляем пометку в отчет для персонала
                    bonus_text_for_report = promo.get('bonus_text', 'графин')
                    report_text += f"\n\n🚨 ВНИМАНИЕ: Гость идет с бонусом '{bonus_text_for_report}'!"
                    # Отправляем уведомление гостю
                    bot.send_message(user_id, texts.get_group_bonus_text(bonus_text_for_report), parse_mode="Markdown")
            except (ValueError, TypeError) as e:
                logging.warning(f"Не удалось определить кол-во гостей для бонуса: {e}")
                pass # Если кол-во гостей не число, просто игнорируем

            # Отправляем отчет и подтверждение пользователю
            bot.send_message(REPORT_CHAT_ID, report_text)
            bot.send_message(
                user_id,
                texts.BOOKING_CONFIRMATION_SUCCESS,
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            # Очищаем данные пользователя из БД бронирования
            db.remove(User.user_id == user_id)

        elif call.data == "cancel_booking":
            # Просто запускаем процесс заново
            _start_booking_process(call.message.chat.id, user_id)

    # --- Новый, надежный обработчик всех шагов бронирования ---
    @bot.message_handler(func=lambda message: db.contains(User.user_id == message.from_user.id), content_types=['text'])
    def process_booking_step(message: types.Message):
        """
        Перехватывает все сообщения от пользователя, который находится в процессе бронирования.
        """
        user_id = message.from_user.id

        user_entry = db.get(User.user_id == user_id)
        # Доп. проверка на случай, если запись в БД есть, а шага нет
        if not user_entry or not user_entry.get('step'):
            return

        step = user_entry.get('step')
        current_data = user_entry.get('data', {})

        # Словарь-маршрутизатор по шагам
        prompts = {
            'name': {'next_step': 'date', 'prompt': texts.BOOKING_ASK_DATE},
            'date': {'next_step': 'time', 'prompt': texts.BOOKING_ASK_TIME},
            'time': {'next_step': 'guests', 'prompt': texts.BOOKING_ASK_GUESTS},
            'guests': {'next_step': 'phone', 'prompt': texts.BOOKING_ASK_PHONE},
            'phone': {'next_step': 'reason', 'prompt': texts.BOOKING_ASK_REASON},
        }

        # Сохраняем ответ пользователя в его данные
        current_data[step] = message.text

        if step in prompts:
            # Если это не последний шаг, переводим на следующий
            next_step_info = prompts[step]
            db.update({'step': next_step_info['next_step'], 'data': current_data}, User.user_id == user_id)
            bot.send_message(message.chat.id, next_step_info['prompt'])
        elif step == 'reason':
            # Если это был последний шаг, показываем подтверждение
            db.update({'step': 'confirmation', 'data': current_data}, User.user_id == user_id)
            confirmation_text = texts.get_booking_confirmation_text(current_data)
            bot.send_message(
                message.chat.id,
                confirmation_text,
                reply_markup=keyboards.get_booking_confirmation_keyboard()
            )
