# handlers/newsletter_buttons.py
"""
Система управления кнопками для рассылок.
Позволяет добавлять, редактировать и удалять кнопки с UTM-трекингом.
"""
import logging
from typing import Dict, Any
import database
import keyboards
import texts
from config import ADMIN_IDS

class NewsletterButtonsManager:
    def __init__(self, bot):
        self.bot = bot
        self.button_states = {}  # Состояния создания кнопок
        
    def register_handlers(self):
        """Регистрирует обработчики для работы с кнопками."""
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('admin_button_'))
        def handle_button_callbacks(call):
            if call.from_user.id not in ADMIN_IDS:
                self.bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
                return
                
            action = call.data
            self.bot.answer_callback_query(call.id)
            
            parts = action.split('_')
            if len(parts) < 4:
                return
                
            if action.startswith('admin_button_template_'):
                newsletter_id = int(parts[3])
                template = parts[4] if len(parts) > 4 else None
                self._handle_button_template(call.message, newsletter_id, template)
            elif action.startswith('admin_button_add_'):
                newsletter_id = int(parts[3])
                self._start_button_creation(call.message, newsletter_id)
            elif action.startswith('admin_button_finish_'):
                newsletter_id = int(parts[3])
                self._finish_button_setup(call.message, newsletter_id)
            elif action.startswith('admin_button_skip_'):
                newsletter_id = int(parts[3])
                self._skip_buttons(call.message, newsletter_id)
                
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('newsletter_click_'))
        def handle_newsletter_button_clicks(call):
            """Обрабатывает клики по кнопкам в рассылках."""
            try:
                parts = call.data.split('_')
                if len(parts) >= 4:
                    newsletter_id = int(parts[2])
                    button_id = int(parts[3])
                    
                    # Записываем клик в аналитику
                    database.track_newsletter_click(newsletter_id, button_id, call.from_user.id)
                    
                    # Получаем информацию о кнопке
                    button = database.get_newsletter_button_by_id(button_id)
                    if button and button['url']:
                        self.bot.answer_callback_query(
                            call.id,
                            "Переходим по ссылке...",
                            url=button['url']
                        )
                    else:
                        self.bot.answer_callback_query(call.id, "Ссылка недоступна")
                        
            except Exception as e:
                logging.error(f"Ошибка обработки клика по кнопке рассылки: {e}")
                self.bot.answer_callback_query(call.id, "Ошибка перехода")
    
    def _handle_button_template(self, message, newsletter_id, template):
        """Обрабатывает выбор шаблона кнопок."""
        if template == 'website':
            # Добавляем кнопку "Наш сайт"
            button_id = database.add_newsletter_button(
                newsletter_id=newsletter_id,
                text="🌐 Наш сайт",
                url="https://evgenich.ru?utm_source=telegram&utm_medium=newsletter&utm_campaign=website_button",
                utm_source="telegram",
                utm_medium="newsletter",
                utm_campaign="website_button"
            )
            
            if button_id:
                self._update_buttons_display(message, newsletter_id, "Добавлена кнопка 'Наш сайт'")
            else:
                self.bot.send_message(message.chat.id, "Ошибка добавления кнопки")
                
        elif template == 'booking':
            # Добавляем кнопку "Забронировать стол"
            button_id = database.add_newsletter_button(
                newsletter_id=newsletter_id,
                text="📅 Забронировать стол",
                url="https://evgenich.ru/booking?utm_source=telegram&utm_medium=newsletter&utm_campaign=booking_button",
                utm_source="telegram",
                utm_medium="newsletter",
                utm_campaign="booking_button"
            )
            
            if button_id:
                self._update_buttons_display(message, newsletter_id, "Добавлена кнопка 'Забронировать стол'")
            else:
                self.bot.send_message(message.chat.id, "Ошибка добавления кнопки")
                
        elif template == 'menu':
            # Добавляем кнопку "Посмотреть меню"
            button_id = database.add_newsletter_button(
                newsletter_id=newsletter_id,
                text="🍽 Посмотреть меню",
                url="https://evgenich.ru/menu?utm_source=telegram&utm_medium=newsletter&utm_campaign=menu_button",
                utm_source="telegram",
                utm_medium="newsletter",
                utm_campaign="menu_button"
            )
            
            if button_id:
                self._update_buttons_display(message, newsletter_id, "Добавлена кнопка 'Посмотреть меню'")
            else:
                self.bot.send_message(message.chat.id, "Ошибка добавления кнопки")
                
        elif template == 'promotion':
            # Добавляем кнопку "Узнать подробности"
            button_id = database.add_newsletter_button(
                newsletter_id=newsletter_id,
                text="🎁 Узнать подробности",
                url="https://evgenich.ru/promo?utm_source=telegram&utm_medium=newsletter&utm_campaign=promo_button",
                utm_source="telegram",
                utm_medium="newsletter",
                utm_campaign="promo_button"
            )
            
            if button_id:
                self._update_buttons_display(message, newsletter_id, "Добавлена кнопка 'Узнать подробности'")
            else:
                self.bot.send_message(message.chat.id, "Ошибка добавления кнопки")
                
        elif template == 'contact':
            # Добавляем кнопку "Связаться с нами"
            button_id = database.add_newsletter_button(
                newsletter_id=newsletter_id,
                text="📞 Связаться с нами",
                url="https://evgenich.ru/contact?utm_source=telegram&utm_medium=newsletter&utm_campaign=contact_button",
                utm_source="telegram",
                utm_medium="newsletter",
                utm_campaign="contact_button"
            )
            
            if button_id:
                self._update_buttons_display(message, newsletter_id, "Добавлена кнопка 'Связаться с нами'")
            else:
                self.bot.send_message(message.chat.id, "Ошибка добавления кнопки")
    
    def _start_button_creation(self, message, newsletter_id):
        """Начинает создание пользовательской кнопки."""
        user_id = message.chat.id
        self.button_states[user_id] = {
            'newsletter_id': newsletter_id,
            'step': 'text'
        }
        
        self.bot.send_message(
            user_id,
            texts.BUTTON_TEXT_REQUEST,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(message, self._handle_button_text_input)
    
    def _handle_button_text_input(self, message):
        """Обрабатывает ввод текста кнопки."""
        user_id = message.chat.id
        if user_id not in self.button_states:
            self.bot.send_message(user_id, "Сессия создания кнопки истекла")
            return
        
        text = message.text.strip()
        if not text or len(text) > 30:
            self.bot.send_message(
                user_id,
                "Текст кнопки должен быть от 1 до 30 символов. Попробуйте еще раз:"
            )
            self.bot.register_next_step_handler(message, self._handle_button_text_input)
            return
        
        self.button_states[user_id]['text'] = text
        self.button_states[user_id]['step'] = 'url'
        
        self.bot.send_message(
            user_id,
            texts.BUTTON_URL_REQUEST,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(message, self._handle_button_url_input)
    
    def _handle_button_url_input(self, message):
        """Обрабатывает ввод URL кнопки."""
        user_id = message.chat.id
        if user_id not in self.button_states:
            self.bot.send_message(user_id, "Сессия создания кнопки истекла")
            return
        
        url = message.text.strip()
        if not url.startswith(('http://', 'https://')):
            self.bot.send_message(
                user_id,
                "URL должен начинаться с http:// или https://. Попробуйте еще раз:"
            )
            self.bot.register_next_step_handler(message, self._handle_button_url_input)
            return
        
        # Добавляем UTM-параметры если их нет
        if 'utm_source' not in url:
            separator = '&' if '?' in url else '?'
            url += f"{separator}utm_source=telegram&utm_medium=newsletter&utm_campaign=custom_button"
        
        state = self.button_states[user_id]
        newsletter_id = state['newsletter_id']
        
        # Создаем кнопку
        button_id = database.add_newsletter_button(
            newsletter_id=newsletter_id,
            text=state['text'],
            url=url,
            utm_source="telegram",
            utm_medium="newsletter",
            utm_campaign="custom_button"
        )
        
        if button_id:
            del self.button_states[user_id]
            # Обновляем отображение кнопок
            buttons = database.get_newsletter_buttons(newsletter_id)
            buttons_text = texts.BUTTON_MANAGEMENT_TEXT.format(
                current_count=len(buttons)
            )
            
            # Список кнопок
            for i, button in enumerate(buttons, 1):
                buttons_text += f"{i}. {button['text']}\n"
            
            self.bot.send_message(
                user_id,
                buttons_text,
                reply_markup=keyboards.get_newsletter_buttons_menu(newsletter_id),
                parse_mode="Markdown"
            )
        else:
            self.bot.send_message(user_id, "Ошибка создания кнопки. Попробуйте еще раз.")
            del self.button_states[user_id]
    
    def _update_buttons_display(self, message, newsletter_id, success_message=None):
        """Обновляет отображение списка кнопок."""
        buttons = database.get_newsletter_buttons(newsletter_id)
        
        buttons_text = texts.BUTTON_MANAGEMENT_TEXT.format(
            current_count=len(buttons)
        )
        
        if success_message:
            buttons_text = f"✅ {success_message}\n\n" + buttons_text
        
        # Список кнопок
        for i, button in enumerate(buttons, 1):
            buttons_text += f"{i}. {button['text']}\n"
        
        self.bot.edit_message_text(
            buttons_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_newsletter_buttons_menu(newsletter_id),
            parse_mode="Markdown"
        )
    
    def _finish_button_setup(self, message, newsletter_id):
        """Завершает настройку кнопок и переходит к финальному меню."""
        from handlers.newsletter_manager import NewsletterManager
        manager = NewsletterManager(self.bot, None)
        manager._show_newsletter_sending_menu(message, newsletter_id)
    
    def _skip_buttons(self, message, newsletter_id):
        """Пропускает добавление кнопок."""
        self._finish_button_setup(message, newsletter_id)

def register_newsletter_buttons_handlers(bot):
    """Регистрирует обработчики для кнопок рассылок."""
    manager = NewsletterButtonsManager(bot)
    manager.register_handlers()
    logging.info("Обработчики кнопок рассылок зарегистрированы")
