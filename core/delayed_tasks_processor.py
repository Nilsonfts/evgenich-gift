# delayed_tasks_processor.py
"""
Обработчик отложенных задач для бота Евгенич.
Запускается в фоновом режиме и отправляет запланированные сообщения.
"""
import time
import threading
import logging
from typing import TYPE_CHECKING
from .database import get_pending_delayed_tasks, mark_delayed_task_completed, cleanup_old_delayed_tasks
from texts import DELAYED_ENGAGEMENT_TEXT

if TYPE_CHECKING:
    import telebot

class DelayedTasksProcessor:
    def __init__(self, bot: "telebot.TeleBot"):
        self.bot = bot
        self.running = False
        self.thread = None
        
    def start(self):
        """Запускает обработчик отложенных задач."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_tasks_loop, daemon=True)
        self.thread.start()
        logging.info("Обработчик отложенных задач запущен")
        
    def stop(self):
        """Останавливает обработчик отложенных задач."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logging.info("Обработчик отложенных задач остановлен")
        
    def _process_tasks_loop(self):
        """Основной цикл обработки задач."""
        while self.running:
            try:
                # Проверяем отложенные задачи каждые 30 секунд
                self._process_pending_tasks()
                
                # Раз в час очищаем старые задачи
                cleanup_old_delayed_tasks()
                
                time.sleep(30)
            except Exception as e:
                logging.error(f"Ошибка в цикле обработки отложенных задач: {e}")
                time.sleep(60)  # При ошибке ждем дольше
                
    def _process_pending_tasks(self):
        """Обрабатывает все готовые к выполнению задачи."""
        pending_tasks = get_pending_delayed_tasks()
        
        for task in pending_tasks:
            try:
                self._execute_task(task)
                mark_delayed_task_completed(task['id'])
            except Exception as e:
                logging.error(f"Ошибка выполнения задачи {task['id']}: {e}")
                
    def _execute_task(self, task):
        """Выполняет конкретную задачу."""
        user_id = task['user_id']
        task_type = task['task_type']
        
        if task_type == 'engagement_after_redeem':
            self._send_engagement_message(user_id)
        elif task_type == 'send_newsletter':
            self._send_newsletter_message(user_id, task)
        else:
            logging.warning(f"Неизвестный тип задачи: {task_type}")
            
    def _send_engagement_message(self, user_id: int):
        """Отправляет вовлекающее сообщение с картой лояльности после погашения купона."""
        try:
            import keyboards
            self.bot.send_message(
                user_id,
                DELAYED_ENGAGEMENT_TEXT,
                parse_mode='Markdown',
                reply_markup=keyboards.get_loyalty_keyboard()
            )
            logging.info(f"Отправлено вовлекающее сообщение с картой лояльности пользователю {user_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки вовлекающего сообщения пользователю {user_id}: {e}")
    
    def _send_newsletter_message(self, user_id: int, task):
        """Отправляет рассылку пользователю."""
        try:
            from . import database
            import keyboards
            
            # Получаем данные рассылки
            newsletter_id = task.get('newsletter_id')
            if not newsletter_id:
                logging.error("Newsletter ID не указан в задаче")
                return
                
            newsletter = database.get_newsletter_by_id(newsletter_id)
            if not newsletter:
                logging.error(f"Рассылка {newsletter_id} не найдена")
                return
            
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
            
            # Фиксируем доставку
            database.track_newsletter_delivery(newsletter_id, user_id)
            logging.info(f"Отправлена рассылка {newsletter_id} пользователю {user_id}")
            
        except Exception as e:
            logging.error(f"Ошибка отправки рассылки пользователю {user_id}: {e}")
