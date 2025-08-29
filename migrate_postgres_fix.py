#!/usr/bin/env python3
"""
Миграция PostgreSQL для добавления отсутствующих колонок
"""
import logging
import os
import sys
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from config import DATABASE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def migrate_postgres():
    """Выполняет миграцию PostgreSQL для добавления отсутствующих колонок."""
    if not DATABASE_URL:
        logging.error("DATABASE_URL не установлен!")
        return False
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Проверяем и добавляем отсутствующие колонки в таблицу users
            missing_columns = [
                ("referrer_rewarded", "BOOLEAN DEFAULT FALSE"),
                ("referrer_rewarded_date", "TIMESTAMP"),
                ("utm_source", "TEXT"),
                ("utm_medium", "TEXT"),
                ("utm_campaign", "TEXT"),
                ("phone_number", "TEXT"),
                ("contact_shared_date", "TIMESTAMP"),
                ("real_name", "TEXT"),
                ("birth_date", "DATE"),
                ("profile_completed", "BOOLEAN DEFAULT FALSE"),
                ("ai_concept", "TEXT DEFAULT 'evgenich'"),
            ]
            
            for column_name, column_type in missing_columns:
                try:
                    # Проверяем, существует ли колонка
                    result = conn.execute(text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='{column_name}'
                    """))
                    
                    if not result.fetchone():
                        # Добавляем колонку, если её нет
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
                        logging.info(f"✅ Добавлена колонка users.{column_name}")
                    else:
                        logging.info(f"⚪ Колонка users.{column_name} уже существует")
                
                except Exception as e:
                    logging.error(f"❌ Ошибка добавления колонки {column_name}: {e}")
            
            # Проверяем и создаем недостающие таблицы
            tables_to_create = {
                "newsletters": """
                    CREATE TABLE IF NOT EXISTS newsletters (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        media_type TEXT,
                        media_file_id TEXT,
                        status TEXT DEFAULT 'draft',
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        scheduled_time TIMESTAMP,
                        sent_at TIMESTAMP,
                        target_count INTEGER DEFAULT 0,
                        sent_count INTEGER DEFAULT 0
                    )
                """,
                "newsletter_targets": """
                    CREATE TABLE IF NOT EXISTS newsletter_targets (
                        id SERIAL PRIMARY KEY,
                        newsletter_id INTEGER REFERENCES newsletters(id),
                        user_id INTEGER,
                        status TEXT DEFAULT 'pending',
                        sent_at TIMESTAMP,
                        error_message TEXT
                    )
                """,
                "conversation_history": """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        role TEXT,
                        text TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "feedback": """
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        rating INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "delayed_tasks": """
                    CREATE TABLE IF NOT EXISTS delayed_tasks (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        task_type TEXT,
                        scheduled_time TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "iiko_data": """
                    CREATE TABLE IF NOT EXISTS iiko_data (
                        id SERIAL PRIMARY KEY,
                        report_date DATE,
                        nastoika_count INTEGER,
                        reported_by_user_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "staff": """
                    CREATE TABLE IF NOT EXISTS staff (
                        staff_id SERIAL PRIMARY KEY,
                        telegram_id INTEGER UNIQUE,
                        full_name TEXT,
                        short_name TEXT,
                        position TEXT,
                        unique_code TEXT UNIQUE,
                        status TEXT DEFAULT 'active'
                    )
                """
            }
            
            for table_name, create_sql in tables_to_create.items():
                try:
                    conn.execute(text(create_sql))
                    logging.info(f"✅ Создана/проверена таблица {table_name}")
                except Exception as e:
                    logging.error(f"❌ Ошибка создания таблицы {table_name}: {e}")
            
            # Фиксируем изменения
            conn.commit()
            logging.info("🎉 Миграция PostgreSQL завершена успешно!")
            return True
            
    except Exception as e:
        logging.error(f"❌ Критическая ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    success = migrate_postgres()
    if success:
        print("✅ Миграция выполнена успешно!")
        sys.exit(0)
    else:
        print("❌ Миграция не удалась!")
        sys.exit(1)
