# /handlers/booking_flow.py

import logging
from telebot import types
from tinydb import TinyDB, Query

# Импортируем конфиги, тексты и клавиатуры
from config import REPORT_CHAT_ID
import texts
import keyboards

# --- Инициализация базы данных для бронирований ---
# Создаст файл "booking_data.json" в корневой папке проекта
db = TinyDB('booking_data.json')
User = Query()

# --- Регистрация обработчиков ---

def register_booking_handlers(bot):
    """
    Регистрирует полный цикл обработчиков для пошагового бронирования стола.
    """

    def _start_booking_process(message):
        """Начинает или перезапускает процесс бронирования для пользователя."""
        user_id = message.from_user.id
        db.upsert({'user_id': user_id, 'step': 'name', 'data': {}}, User.user_id == user_id)
        msg = bot.send_message(message.chat.id, texts.BOOKING_START_PROMPT, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_booking_step)

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

    # --- Обработчик команды /cancel ---
    @bot.message_handler(commands=['cancel'])
    def handle_cancel_command(message: types.Message):
        _cancel_booking(message)

    # --- Точка входа в бронирование ---
    @bot.message_handler(commands=['book'])
    @bot.message_handler(func=lambda message: message.text == "📍 Забронировать стол")
    def handle_booking_entry(message: types.Message):
        """Запускает флоу бронирования, показывая начальные варианты."""
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, texts.BOOKING_IN_PROGRESS_TEXT)
            return
        
        logging.info(f"Пользователь {message.from_user.id} нажал 'Забронировать стол'.")
        bot.send_message(
            message.chat.id, 
            texts.BOOKING_PROMPT_TEXT, 
            reply_markup=keyboards.get_booking_options_keyboard()
        )

    # --- Обработка выбора варианта бронирования ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("booking_"))
    def handle_booking_option_callback(call: types.CallbackQuery):
        """Обрабатывает выбор пользователя (позвонить, сайт, бот) и запускает сбор данных."""
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

        if call.data == "booking_phone":
            bot.send_message(call.message.chat.id, texts.BOOKING_PHONE_TEXT, parse_mode="Markdown")
        elif call.data == "booking_site":
            bot.send_message(call.message.chat.id, texts.BOOKING_SITE_TEXT)
        elif call.data == "booking_secret":
            bot.send_message(call.message.chat.id, texts.BOOKING_SECRET_CHAT_TEXT, reply_markup=keyboards.get_secret_chat_keyboard())
        elif call.data == "booking_bot":
            _start_booking_process(call.message)

    # --- Главный обработчик шагов ---
    def process_booking_step(message: types.Message):
        """
        Единая функция для обработки всех шагов.
        Определяет текущий шаг пользователя и запрашивает следующие данные.
        """
        user_id = message.from_user.id
        
        if message.text == '/cancel':
            return _cancel_booking(message)

        user_entry = db.get(User.user_id == user_id)
        if not user_entry:
            return # Пользователь не находится в процессе бронирования

        step = user_entry.get('step')
        current_data = user_entry.get('data', {})

        prompts = {
            'name': {'next_step': 'date', 'prompt': texts.BOOKING_ASK_DATE},
            'date': {'next_step': 'time', 'prompt': texts.BOOKING_ASK_TIME},
            'time': {'next_step': 'guests', 'prompt': texts.BOOKING_ASK_GUESTS},
            'guests': {'next_step': 'phone', 'prompt': texts.BOOKING_ASK_PHONE},
            'phone': {'next_step': 'reason', 'prompt': texts.BOOKING_ASK_REASON},
        }

        # Сохраняем ответ пользователя
        current_data[step] = message.text
        
        # Определяем следующий шаг
        if step in prompts:
            next_step_info = prompts[step]
            db.update({'step': next_step_info['next_step'], 'data': current_data}, User.user_id == user_id)
            msg = bot.send_message(message.chat.id, next_step_info['prompt'])
            bot.register_next_step_handler(msg, process_booking_step)
        else: # Последний шаг - 'reason'
            db.update({'step': 'confirmation', 'data': current_data}, User.user_id == user_id)
            confirmation_text = texts.get_booking_confirmation_text(current_data)
            bot.send_message(
                message.chat.id, 
                confirmation_text, 
                reply_markup=keyboards.get_booking_confirmation_keyboard()
            )

    # --- Обработка финального подтверждения ---
    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_booking", "cancel_booking"])
    def handle_booking_confirmation_callback(call: types.CallbackQuery):
        """Обрабатывает финальное решение пользователя: подтвердить или начать заново."""
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

        user_entry = db.get(User.user_id == user_id)
        if not user_entry:
            return

        if call.data == "confirm_booking":
            booking_data = user_entry.get('data', {})
            report_text = texts.get_booking_report_text(booking_data)
            
            # Отправляем заявку в чат админам
            bot.send_message(REPORT_CHAT_ID, report_text)
            
            # Сообщаем пользователю об успехе
            bot.send_message(
                user_id, 
                texts.BOOKING_CONFIRMATION_SUCCESS,
                reply_markup=keyboards.get_main_menu_keyboard(user_id)
            )
            
            # Удаляем данные из временной БД
            db.remove(User.user_id == user_id)
            
        elif call.data == "cancel_booking":
            # Просто запускаем процесс заново
            _start_booking_process(call.message)
