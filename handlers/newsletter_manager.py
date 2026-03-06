# handlers/newsletter_manager.py
"""
Система управления рассылками для бота Евгенич.
Включает создание, отправку, планирование и аналитику рассылок.
"""
import logging
import datetime
import pytz
from typing import Optional, Dict, Any
from telebot import types
import core.database as database
import keyboards
import texts
from core.config import ALL_ADMINS

class NewsletterManager:
    def __init__(self, bot, scheduler):
        self.bot = bot
        self.scheduler = scheduler
        self.creation_states = {}  # Состояния создания рассылок
        
    def register_handlers(self):
        """Регистрирует все обработчики для системы рассылок."""
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('admin_content_'))
        def handle_content_callbacks(call):
            if call.from_user.id not in ALL_ADMINS:
                self.bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
                return
                
            action = call.data
            self.bot.answer_callback_query(call.id)
            
            if action == 'admin_content_stats':
                self._show_audience_stats(call.message)
            elif action == 'admin_content_create':
                self._start_newsletter_creation(call.message)
            elif action == 'admin_content_list':
                self._show_newsletters_list(call.message)
            elif action == 'admin_content_analytics':
                self._show_analytics_overview(call.message)
                
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('admin_newsletter_'))
        def handle_newsletter_callbacks(call):
            if call.from_user.id not in ALL_ADMINS:
                self.bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
                return
                
            action = call.data
            self.bot.answer_callback_query(call.id)
            
            if action.startswith('admin_newsletter_type_'):
                media_type = action.split('_')[-1]
                self._handle_newsletter_type_selection(call.message, media_type)
            elif action.startswith('admin_newsletter_test_'):
                newsletter_id = int(action.split('_')[-1])
                self._send_test_newsletter(call.message, newsletter_id)
            elif action.startswith('admin_newsletter_send_'):
                newsletter_id = int(action.split('_')[-1])
                self._send_newsletter_immediately(call.message, newsletter_id)
            elif action.startswith('admin_newsletter_schedule_'):
                newsletter_id = int(action.split('_')[-1])
                self._start_newsletter_scheduling(call.message, newsletter_id)
            elif action.startswith('admin_newsletter_view_'):
                newsletter_id = int(action.split('_')[-1])
                self._show_newsletter_details(call.message, newsletter_id)
            elif action.startswith('admin_newsletter_stats_'):
                newsletter_id = int(action.split('_')[-1])
                self._show_newsletter_analytics(call.message, newsletter_id)
            elif action.startswith('admin_newsletter_ready_'):
                newsletter_id = int(action.split('_')[-1])
                self._show_newsletter_sending_menu(call.message, newsletter_id)

        # NOTE: admin_button_* обработчик находится в newsletter_buttons.py
        # Не дублируем его здесь, чтобы избежать конфликта регистрации
        
        logging.info("Обработчики системы рассылок зарегистрированы")
    
    def _show_audience_stats(self, message):
        """Показывает статистику базы для рассылок."""
        try:
            audience_count = database.get_newsletter_audience_count()
            
            # Дополнительная статистика
            conn = database.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'registered'")
            registered_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status IN ('issued', 'redeemed')")
            active_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed_and_left'")
            churned_count = cur.fetchone()[0]
            
            conn.close()
            
            stats_text = (
                f"{texts.CONTENT_STATS_TEXT}"
                f"**Всего активных подписчиков:** {audience_count}\n\n"
                f"**Детализация:**\n"
                f"• Зарегистрированы: {registered_count}\n"
                f"• Получили купоны: {active_count}\n"
                f"• Отписались: {churned_count}\n\n"
                f"📧 Рассылка будет отправлена **{audience_count}** подписчикам"
            )
            
            self.bot.edit_message_text(
                stats_text,
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_content_management_menu(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка показа статистики аудитории: {e}")
            self.bot.send_message(message.chat.id, "Ошибка получения статистики")
    
    def _start_newsletter_creation(self, message):
        """Начинает процесс создания рассылки."""
        try:
            self.bot.edit_message_text(
                texts.NEWSLETTER_CREATION_START,
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_newsletter_creation_menu(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка начала создания рассылки: {e}")
    
    def _handle_newsletter_type_selection(self, message, media_type):
        """Обрабатывает выбор типа рассылки."""
        user_id = message.chat.id
        self.creation_states[user_id] = {
            'step': 'title',
            'media_type': media_type,
            'created_at': datetime.datetime.now()
        }
        
        # Отправляем инструкцию с примерами в зависимости от типа
        if media_type == 'text':
            instruction = (
                "📝 **Создание текстовой рассылки**\n\n"
                "Введите заголовок рассылки (до 100 символов).\n\n"
                "💡 **Примеры хороших заголовков:**\n"
                "• 🎉 Скидка 20% только сегодня!\n"
                "• 🍽 Новое меню в Евгениче\n"
                "• 🎁 Подарок от шеф-повара\n"
                "• 📅 Бронирование на выходные открыто"
            )
        elif media_type == 'photo':
            instruction = (
                "🖼 **Создание рассылки с картинкой**\n\n"
                "Введите заголовок рассылки (до 100 символов).\n\n"
                "💡 **Рассылки с фото отлично работают для:**\n"
                "• Презентации новых блюд\n"
                "• Показа атмосферы ресторана\n"
                "• Демонстрации акций и предложений\n"
                "• Анонса мероприятий"
            )
        else:  # video
            instruction = (
                "🎥 **Создание рассылки с видео**\n\n"
                "Введите заголовок рассылки (до 100 символов).\n\n"
                "💡 **Видео отлично подходит для:**\n"
                "• Процесса приготовления блюд\n"
                "• Обзора ресторана\n"
                "• Отзывов довольных гостей\n"
                "• Анонса событий и концертов"
            )
        
        self.bot.send_message(
            user_id,
            instruction,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(message, self._handle_title_input)
    
    def _handle_title_input(self, message):
        """Обрабатывает ввод заголовка рассылки."""
        user_id = message.chat.id
        if user_id not in self.creation_states:
            self.bot.send_message(user_id, "Сессия создания рассылки истекла. Начните заново.")
            return
            
        title = message.text.strip()
        if not title or len(title) > 100:
            self.bot.send_message(
                user_id, 
                "Заголовок должен быть от 1 до 100 символов. Попробуйте еще раз:"
            )
            self.bot.register_next_step_handler(message, self._handle_title_input)
            return
        
        self.creation_states[user_id]['title'] = title
        self.creation_states[user_id]['step'] = 'content'
        
        self.bot.send_message(
            user_id,
            texts.NEWSLETTER_CONTENT_REQUEST,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(message, self._handle_content_input)
    
    def _handle_content_input(self, message):
        """Обрабатывает ввод содержания рассылки."""
        user_id = message.chat.id
        if user_id not in self.creation_states:
            self.bot.send_message(user_id, "Сессия создания рассылки истекла. Начните заново.")
            return
        
        content = message.text.strip()
        if not content or len(content) > 4000:
            self.bot.send_message(
                user_id,
                "Текст должен быть от 1 до 4000 символов. Попробуйте еще раз:"
            )
            self.bot.register_next_step_handler(message, self._handle_content_input)
            return
            
        self.creation_states[user_id]['content'] = content
        
        # Если нужно медиа - запрашиваем, иначе переходим к кнопкам
        if self.creation_states[user_id]['media_type'] != 'text':
            self.creation_states[user_id]['step'] = 'media'
            
            media_type = self.creation_states[user_id]['media_type']
            if media_type == 'photo':
                instruction = (
                    "🖼 **Загрузите изображение**\n\n"
                    "📎 Прикрепите картинку к сообщению\n\n"
                    "💡 **Рекомендации:**\n"
                    "• Размер: не более 10 МБ\n"
                    "• Формат: JPG, PNG\n"
                    "• Качество: высокое разрешение\n"
                    "• Содержание: яркое, привлекательное"
                )
            else:  # video
                instruction = (
                    "🎥 **Загрузите видео**\n\n"
                    "📎 Прикрепите видеофайл к сообщению\n\n"
                    "💡 **Рекомендации:**\n"
                    "• Размер: не более 50 МБ\n"
                    "• Длительность: до 60 секунд\n"
                    "• Качество: HD (минимум 720p)\n"
                    "• Звук: четкий, без шумов"
                )
            
            self.bot.send_message(
                user_id,
                instruction,
                parse_mode="Markdown"
            )
            self.bot.register_next_step_handler(message, self._handle_media_input)
        else:
            self._proceed_to_buttons_step(user_id)
    
    def _handle_media_input(self, message):
        """Обрабатывает загрузку медиа-файла."""
        user_id = message.chat.id
        if user_id not in self.creation_states:
            self.bot.send_message(user_id, "Сессия создания рассылки истекла. Начните заново.")
            return
        
        media_type = self.creation_states[user_id]['media_type']
        file_id = None
        
        if media_type == 'photo' and message.photo:
            file_id = message.photo[-1].file_id
        elif media_type == 'video' and message.video:
            file_id = message.video.file_id
        else:
            expected = "картинку" if media_type == 'photo' else "видео"
            self.bot.send_message(
                user_id,
                f"Пожалуйста, отправьте {expected}. Попробуйте еще раз:"
            )
            self.bot.register_next_step_handler(message, self._handle_media_input)
            return
        
        self.creation_states[user_id]['media_file_id'] = file_id
        self._proceed_to_buttons_step(user_id)
    
    def _proceed_to_buttons_step(self, user_id):
        """Переходит к этапу добавления кнопок."""
        self.creation_states[user_id]['step'] = 'buttons'
        
        # Создаем рассылку в БД
        state = self.creation_states[user_id]
        newsletter_id = database.create_newsletter(
            title=state['title'],
            content=state['content'],
            created_by=user_id,
            media_type=state.get('media_type') if state['media_type'] != 'text' else None,
            media_file_id=state.get('media_file_id')
        )
        
        if newsletter_id:
            self.creation_states[user_id]['newsletter_id'] = newsletter_id
            
            self.bot.send_message(
                user_id,
                texts.NEWSLETTER_BUTTONS_PROMPT,
                reply_markup=keyboards.get_newsletter_buttons_menu(newsletter_id),
                parse_mode="Markdown"
            )
        else:
            self.bot.send_message(user_id, "Ошибка создания рассылки. Попробуйте еще раз.")
            del self.creation_states[user_id]
    
    def _show_newsletter_sending_menu(self, message, newsletter_id):
        """Показывает меню отправки готовой рассылки."""
        newsletter = database.get_newsletter_by_id(newsletter_id)
        if not newsletter:
            self.bot.send_message(message.chat.id, "Рассылка не найдена")
            return
        
        buttons = database.get_newsletter_buttons(newsletter_id)
        audience_count = database.get_newsletter_audience_count()
        
        content_preview = newsletter['content'][:100] + "..." if len(newsletter['content']) > 100 else newsletter['content']
        media_status = "Есть" if newsletter['media_file_id'] else "Нет"
        
        ready_text = texts.NEWSLETTER_READY_TEXT.format(
            title=newsletter['title'],
            content_preview=content_preview,
            media_status=media_status,
            buttons_count=len(buttons),
            audience_count=audience_count
        )
        
        self.bot.edit_message_text(
            ready_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_newsletter_sending_menu(newsletter_id),
            parse_mode="Markdown"
        )
    
    def _send_test_newsletter(self, message, newsletter_id):
        """Отправляет тестовую рассылку админу."""
        newsletter = database.get_newsletter_by_id(newsletter_id)
        if not newsletter:
            self.bot.send_message(message.chat.id, "Рассылка не найдена")
            return
        
        success = self._send_newsletter_to_user(message.chat.id, newsletter_id)
        if success:
            self.bot.send_message(
                message.chat.id,
                texts.NEWSLETTER_TEST_SENT,
                parse_mode="Markdown"
            )
        else:
            self.bot.send_message(message.chat.id, "Ошибка отправки тестового сообщения")
    
    def _send_newsletter_immediately(self, message, newsletter_id):
        """Начинает немедленную отправку рассылки."""
        self.bot.send_message(
            message.chat.id,
            texts.NEWSLETTER_SENDING_START,
            parse_mode="Markdown"
        )
        
        # Запускаем отправку в фоне
        self.scheduler.add_job(
            func=lambda: self._execute_newsletter_sending(newsletter_id, message.chat.id),
            trigger='date',
            run_date=datetime.datetime.now() + datetime.timedelta(seconds=2),
            id=f'newsletter_send_{newsletter_id}',
            replace_existing=True
        )
    
    def _execute_newsletter_sending(self, newsletter_id, admin_chat_id):
        """Выполняет массовую отправку рассылки."""
        try:
            user_ids = database.get_active_users_for_newsletter()
            delivered_count = 0
            failed_count = 0
            
            for user_id in user_ids:
                try:
                    if self._send_newsletter_to_user(user_id, newsletter_id):
                        delivered_count += 1
                        database.track_newsletter_delivery(newsletter_id, user_id)
                    else:
                        failed_count += 1
                    
                    # Пауза между отправками для соблюдения лимитов Telegram
                    import time
                    time.sleep(0.1)
                    
                except Exception as e:
                    logging.error(f"Ошибка отправки рассылки {newsletter_id} пользователю {user_id}: {e}")
                    failed_count += 1
            
            # Обновляем статистику рассылки
            database.mark_newsletter_sent(newsletter_id, len(user_ids), delivered_count)
            
            # Уведомляем админа о результатах
            result_text = texts.NEWSLETTER_SENDING_COMPLETE.format(
                target=len(user_ids),
                delivered=delivered_count,
                failed=failed_count
            )
            
            self.bot.send_message(admin_chat_id, result_text, parse_mode="Markdown")
            
        except Exception as e:
            logging.error(f"Ошибка выполнения рассылки {newsletter_id}: {e}")
            self.bot.send_message(admin_chat_id, "Ошибка при выполнении рассылки")
    
    def _send_newsletter_to_user(self, user_id: int, newsletter_id: int) -> bool:
        """Отправляет рассылку конкретному пользователю."""
        try:
            newsletter = database.get_newsletter_by_id(newsletter_id)
            if not newsletter:
                return False
            
            buttons = database.get_newsletter_buttons(newsletter_id)
            keyboard = keyboards.create_newsletter_inline_keyboard(buttons) if buttons else None
            
            # Отправляем в зависимости от типа медиа
            if newsletter['media_type'] == 'photo':
                self.bot.send_photo(
                    user_id,
                    newsletter['media_file_id'],
                    caption=newsletter['content'],
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            elif newsletter['media_type'] == 'video':
                self.bot.send_video(
                    user_id,
                    newsletter['media_file_id'],
                    caption=newsletter['content'],
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                self.bot.send_message(
                    user_id,
                    newsletter['content'],
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            
            return True
            
        except Exception as e:
            logging.error(f"Ошибка отправки рассылки {newsletter_id} пользователю {user_id}: {e}")
            return False
    
    def _show_newsletters_list(self, message):
        """Показывает список рассылок пользователя."""
        newsletters = database.get_user_newsletters(message.chat.id, 10)
        
        if not newsletters:
            self.bot.edit_message_text(
                texts.NO_NEWSLETTERS_TEXT,
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_content_management_menu(),
                parse_mode="Markdown"
            )
            return
        
        list_text = "📋 **Ваши рассылки:**\n\n"
        for newsletter in newsletters[:5]:  # Показываем только первые 5
            status_text = {
                'draft': 'Черновик',
                'scheduled': 'Запланирована',
                'sent': 'Отправлена',
                'sending': 'Отправляется'
            }.get(newsletter['status'], 'Неизвестно')
            
            list_text += f"• **{newsletter['title']}** ({status_text})\n"
        
        self.bot.edit_message_text(
            list_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_newsletter_list_keyboard(newsletters),
            parse_mode="Markdown"
        )
    
    def _show_newsletter_analytics(self, message, newsletter_id):
        """Показывает аналитику конкретной рассылки."""
        newsletter = database.get_newsletter_by_id(newsletter_id)
        if not newsletter:
            self.bot.send_message(message.chat.id, "Рассылка не найдена")
            return
        
        analytics = database.get_newsletter_analytics(newsletter_id)
        
        analytics_text = texts.NEWSLETTER_ANALYTICS_HEADER.format(
            title=newsletter['title'],
            target_count=analytics['target_count'],
            delivered_count=analytics['delivered_count'],
            total_clicks=analytics['total_clicks']
        )
        
        if analytics['button_stats']:
            for button_stat in analytics['button_stats']:
                analytics_text += f"• {button_stat['text']}: {button_stat['clicks']} кликов\n"
        else:
            analytics_text += "• Кнопок нет\n"
        
        if analytics['delivered_count'] > 0:
            ctr = round(analytics['total_clicks'] / analytics['delivered_count'] * 100, 1)
            analytics_text += f"\n**CTR (кликабельность):** {ctr}%"
        
        self.bot.edit_message_text(
            analytics_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_newsletter_view_keyboard(newsletter_id, newsletter['status']),
            parse_mode="Markdown"
        )
    
    def _show_analytics_overview(self, message):
        """Показывает общую аналитику всех рассылок."""
        newsletters = database.get_user_newsletters(message.chat.id, 20)
        
        if not newsletters:
            self.bot.edit_message_text(
                "📈 **Общая аналитика**\n\nУ вас пока нет рассылок для анализа.",
                message.chat.id,
                message.message_id,
                reply_markup=keyboards.get_content_management_menu(),
                parse_mode="Markdown"
            )
            return
        
        total_sent = sum(n['target_count'] or 0 for n in newsletters if n['status'] == 'sent')
        total_delivered = sum(n['delivered_count'] or 0 for n in newsletters if n['status'] == 'sent')
        
        overview_text = (
            f"📈 **Общая аналитика рассылок**\n\n"
            f"**Всего рассылок:** {len(newsletters)}\n"
            f"**Отправлено сообщений:** {total_sent}\n"
            f"**Доставлено:** {total_delivered}\n\n"
            f"**Последние рассылки:**\n"
        )
        
        for newsletter in newsletters[:5]:
            status_emoji = {'draft': '📝', 'scheduled': '⏰', 'sent': '✅'}.get(newsletter['status'], '❓')
            overview_text += f"{status_emoji} {newsletter['title'][:30]}...\n"
        
        self.bot.edit_message_text(
            overview_text,
            message.chat.id,
            message.message_id,
            reply_markup=keyboards.get_content_management_menu(),
            parse_mode="Markdown"
        )

def register_newsletter_handlers(bot, scheduler):
    """Регистрирует обработчики системы рассылок."""
    manager = NewsletterManager(bot, scheduler)
    manager.register_handlers()
    logging.info("Система рассылок инициализирована")
