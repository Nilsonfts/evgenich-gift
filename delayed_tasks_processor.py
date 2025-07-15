# delayed_tasks_processor.py
"""
Обработчик отложенных задач для бота Евгенич.
Запускается в фоновом режиме и отправляет запланированные сообщения.
"""
import time
import threading
import logging
from typing import TYPE_CHECKING
from database import get_pending_delayed_tasks, mark_delayed_task_completed, cleanup_old_delayed_tasks
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
        else:
            logging.warning(f"Неизвестный тип задачи: {task_type}")
            
    def _send_engagement_message(self, user_id: int):
        """Отправляет вовлекающее сообщение после погашения купона."""
        try:
            self.bot.send_message(
                user_id,
                DELAYED_ENGAGEMENT_TEXT,
                parse_mode='Markdown'
            )
            logging.info(f"Отправлено вовлекающее сообщение пользователю {user_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки вовлекающего сообщения пользователю {user_id}: {e}")
