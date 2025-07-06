# /handlers/ai_logic.py

import logging
from telebot import types
from tinydb import TinyDB, Query

# Импортируем "мозг"
from ai_assistant import get_ai_recommendation
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA

# Импортируем нужные функции, тексты и клавиатуры
from g_sheets import log_conversation_turn, get_conversation_history, get_daily_updates
import texts
import keyboards

# Подключаемся к той же БД, что и в booking_flow, чтобы проверять, не занят ли юзер
db = TinyDB('booking_data.json')
User = Query()

def register_ai_handlers(bot):
    """
    Регистрирует обработчики для AI-ассистента и других текстовых кнопок.
    """
    
    # --- Сначала обработаем кнопки, которые маскируются под текст ---
    
    @bot.message_handler(func=lambda message: message.text == "🗣 Спроси у Евгенича")
    def handle_ai_prompt_button(message: types.Message):
        """Обрабатывает нажатие на кнопку-подсказку для ИИ."""
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, texts.BOOKING_IN_PROGRESS_TEXT)
            return
        bot.reply_to(message, texts.AI_PROMPT_HINT)

    # --- Главный обработчик всех остальных текстовых сообщений ---
    # Он должен быть одним из последних, чтобы не перехватывать команды
    
    @bot.message_handler(content_types=['text'])
    def handle_text_query(message: types.Message):
        user_id = message.from_user.id
        user_text = message.text

        # 1. Проверяем, не находится ли пользователь в процессе бронирования
        if db.contains(User.user_id == user_id):
            # Если да, то этот хендлер не должен ничего делать.
            # Логика register_next_step_handler в booking_flow сама всё обработает.
            return
        
        # 2. Проверяем, не является ли текст командой или известной кнопкой
        # Это "защита от дурака", чтобы AI не отвечал на "📖 Меню" и т.п.
        known_buttons = [
            '📖 Меню', '🤝 Привести товарища', '🗣 Спроси у Евгенича', 
            '🥃 Получить настойку по талону', '📍 Забронировать стол'
        ]
        if user_text.startswith('/') or user_text in known_buttons:
            # Игнорируем, так как это должно быть обработано другими хендлерами
            return 
        
        # 3. Если это обычный текст, запускаем логику AI
        logging.info(f"Пользователь {user_id} отправил текстовый запрос AI: '{user_text}'")
        
        # Логируем запрос пользователя в Google Sheets
        log_conversation_turn(user_id, "user", user_text)
        
        # Получаем историю диалога и оперативные данные (стоп-лист/спецпредложения)
        history = get_conversation_history(user_id, limit=6)
        daily_updates = get_daily_updates()
        
        # Показываем "Евгенич печатает..."
        bot.send_chat_action(message.chat.id, 'typing')

        # Вызываем нейросеть
        ai_response = get_ai_recommendation(
            user_query=user_text,
            conversation_history=history,
            menu_data=MENU_DATA,
            food_menu_data=FOOD_MENU_DATA,
            daily_updates=daily_updates
        )
        
        # 4. Обрабатываем ответ от AI
        if "[START_BOOKING_FLOW]" in ai_response:
            # Если AI решил, что пользователь хочет бронь, запускаем соответствующий флоу
            logging.info(f"AI определил намерение бронирования для пользователя {user_id}.")
            log_conversation_turn(user_id, "assistant", "Предложил варианты бронирования.")
            bot.send_message(
                message.chat.id, 
                texts.BOOKING_PROMPT_TEXT, 
                reply_markup=keyboards.get_booking_options_keyboard()
            )
        else:
            # Иначе просто отправляем ответ
            log_conversation_turn(user_id, "assistant", ai_response)
            bot.reply_to(message, ai_response, parse_mode="Markdown")
