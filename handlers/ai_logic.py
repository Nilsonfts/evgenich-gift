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
    
    @bot.message_handler(func=lambda message: message.text == "🗣 Спроси у Евгенича")
    def handle_ai_prompt_button(message: types.Message):
        """Обрабатывает нажатие на кнопку-подсказку для ИИ."""
        if db.contains(User.user_id == message.from_user.id):
            bot.reply_to(message, texts.BOOKING_IN_PROGRESS_TEXT)
            return
        bot.reply_to(message, texts.AI_PROMPT_HINT)

    @bot.message_handler(content_types=['text'])
    def handle_text_query(message: types.Message):
        user_id = message.from_user.id
        user_text = message.text

        # 1. Проверяем, не находится ли пользователь в процессе бронирования (ЭТА ЛОГИКА ТЕПЕРЬ В booking_flow.py)
        # Если да, то этот хендлер не будет вызван, т.к. хендлер бронирования стоит раньше.
        
        # 2. Проверяем, не является ли текст командой или известной кнопкой
        known_buttons = [
            '📖 Меню', '🤝 Привести товарища', '🗣 Спроси у Евгенича', 
            '🥃 Получить настойку по талону', '📍 Забронировать стол'
        ]
        if user_text.startswith('/') or user_text in known_buttons:
            return 
        
        # 3. Если это обычный текст, запускаем логику AI
        logging.info(f"Пользователь {user_id} отправил текстовый запрос AI: '{user_text}'")
        
        log_conversation_turn(user_id, "user", user_text)
        
        history = get_conversation_history(user_id, limit=6)
        daily_updates = get_daily_updates()
        
        bot.send_chat_action(message.chat.id, 'typing')

        ai_response = get_ai_recommendation(
            user_query=user_text,
            conversation_history=history,
            menu_data=MENU_DATA,
            food_menu_data=FOOD_MENU_DATA,
            daily_updates=daily_updates
        )
        
        # 4. Обрабатываем ответ от AI
        if "[START_BOOKING_FLOW]" in ai_response:
            logging.info(f"AI определил намерение бронирования для пользователя {user_id}.")
            log_conversation_turn(user_id, "assistant", "Предложил варианты бронирования.")
            bot.send_message(
                message.chat.id, 
                texts.BOOKING_PROMPT_TEXT, 
                reply_markup=keyboards.get_booking_options_keyboard()
            )
        else:
            log_conversation_turn(user_id, "assistant", ai_response)
            bot.reply_to(message, ai_response, parse_mode="Markdown")
            
            # --- ИСПРАВЛЕНИЕ: Отправляем кнопки, только если это не ответ-заглушка ---
            if "плёнку зажевало" not in ai_response:
                try:
                    feedback_message = bot.send_message(
                        message.chat.id, 
                        texts.AI_FEEDBACK_PROMPT, 
                        reply_markup=keyboards.get_ai_feedback_keyboard()
                    )
                    
                    if not hasattr(bot, 'feedback_data'):
                        bot.feedback_data = {}
                    
                    bot.feedback_data[feedback_message.message_id] = {
                        'user_id': user_id,
                        'query': user_text,
                        'response': ai_response
                    }
                except Exception as e:
                    logging.error(f"Не удалось отправить кнопки для обратной связи AI: {e}")
