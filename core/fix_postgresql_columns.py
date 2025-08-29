#!/usr/bin/env python3
"""
Миграция для добавления отсутствующих колонок в PostgreSQL на Railway
"""
import os
import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_postgresql_columns():
    """Добавляет отсутствующие колонки в PostgreSQL"""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL не найден в переменных окружения")
        return False
    
    try:
        # Подключаемся к PostgreSQL
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        logger.info("Подключение к PostgreSQL успешно")
        
        # Список колонок для добавления
        columns_to_add = [
            ("referrer_rewarded", "INTEGER DEFAULT 0"),
            ("referrer_rewarded_date", "TEXT"),
            ("utm_source", "TEXT"),
            ("phone_number", "TEXT"),
            ("contact_shared_date", "TIMESTAMP"),
            ("real_name", "TEXT"),
            ("birth_date", "DATE"),
            ("profile_completed", "BOOLEAN DEFAULT FALSE"),
            ("ai_concept", "TEXT DEFAULT 'evgenich'"),
            ("blocked", "INTEGER DEFAULT 0"),
            ("block_date", "TEXT")
        ]
        
        # Добавляем каждую колонку (если она не существует)
        for column_name, column_type in columns_to_add:
            try:
                # Проверяем, существует ли колонка
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name=%s
                """, (column_name,))
                
                if cur.fetchone() is None:
                    # Колонка не существует, добавляем её
                    alter_query = sql.SQL("ALTER TABLE users ADD COLUMN {} {}").format(
                        sql.Identifier(column_name),
                        sql.SQL(column_type)
                    )
                    cur.execute(alter_query)
                    logger.info(f"✅ Добавлена колонка: {column_name}")
                else:
                    logger.info(f"ℹ️  Колонка уже существует: {column_name}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при добавлении колонки {column_name}: {e}")
        
        # Сохраняем изменения
        conn.commit()
        logger.info("🎉 Миграция завершена успешно!")
        
        # Проверяем структуру таблицы
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='users' 
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        logger.info("📋 Текущая структура таблицы users:")
        for col_name, col_type in columns:
            logger.info(f"   {col_name}: {col_type}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    success = fix_postgresql_columns()
    if success:
        print("✅ Миграция выполнена успешно!")
    else:
        print("❌ Ошибка выполнения миграции")
        exit(1)
