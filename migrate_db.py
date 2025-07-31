#!/usr/bin/env python3
"""
Скрипт для запуска миграции данных из SQLite в PostgreSQL.
"""
import logging
import os
from dotenv import load_dotenv

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Загружаем переменные окружения
load_dotenv()

# Устанавливаем переменную окружения для использования PostgreSQL
os.environ["USE_POSTGRES"] = "true"

# Импортируем модуль миграции после установки переменных окружения
from db.migrate_to_postgres import migrate_sqlite_to_postgres

if __name__ == "__main__":
    logging.info("Начинаем миграцию данных из SQLite в PostgreSQL...")
    
    success = migrate_sqlite_to_postgres()
    
    if success:
        logging.info("✅ Миграция успешно завершена!")
        logging.info("Теперь вы можете установить USE_POSTGRES=true в .env файле для использования PostgreSQL")
    else:
        logging.error("❌ Ошибка при выполнении миграции")
        logging.error("Проверьте настройки PostgreSQL и доступность базы данных")
