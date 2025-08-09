#!/usr/bin/env python3
"""
ФИНАЛЬНАЯ МИГРАЦИЯ POSTGRESQL ДЛЯ СИСТЕМЫ РАССЫЛОК
==================================================

Этот скрипт добавляет необходимые колонки для:
- Системы рефералов (referrer_rewarded, referrer_rewarded_date)  
- Системы рассылок (blocked, block_date)

ИСПОЛЬЗОВАНИЕ:
1. В Railway/production: python migrate_postgres_final.py
2. Локально с тестовой БД: DATABASE_URL="your_url" python migrate_postgres_final.py
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Выполняет миграцию PostgreSQL"""
    
    print("🚀 МИГРАЦИЯ POSTGRESQL - СИСТЕМА РАССЫЛОК")
    print("=" * 50)
    
    # Проверяем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        print("💡 Для Railway этот скрипт запустится автоматически")
        print("💡 Для локального тестирования: export DATABASE_URL='your_postgres_url'")
        return False
    
    try:
        # Импортируем PostgreSQL библиотеки
        import psycopg2
        from urllib.parse import urlparse
        
        # Парсим DATABASE_URL
        parsed = urlparse(database_url)
        
        print(f"🔌 Подключение к PostgreSQL...")
        print(f"   Host: {parsed.hostname}")
        print(f"   Database: {parsed.path[1:]}")
        print(f"   User: {parsed.username}")
        
        # Подключение к базе данных
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Подключение установлено")
        
        # Проверяем существующие колонки
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND table_schema = 'public'
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"📋 Существующие колонки таблицы users: {len(existing_columns)}")
        
        # Колонки для добавления
        columns_to_add = [
            ("referrer_rewarded", "BOOLEAN DEFAULT false"),
            ("referrer_rewarded_date", "TIMESTAMP"),
            ("blocked", "BOOLEAN DEFAULT false"), 
            ("block_date", "TIMESTAMP")
        ]
        
        migration_executed = False
        
        for column_name, column_definition in columns_to_add:
            if column_name not in existing_columns:
                sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_definition};"
                print(f"➕ Добавляю колонку: {column_name}")
                cursor.execute(sql)
                migration_executed = True
            else:
                print(f"✅ Колонка {column_name} уже существует")
        
        if migration_executed:
            conn.commit()
            print("💾 Изменения сохранены")
        else:
            print("ℹ️ Все необходимые колонки уже существуют")
        
        # Финальная проверка
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users' AND table_schema = 'public'
            AND column_name IN ('referrer_rewarded', 'referrer_rewarded_date', 'blocked', 'block_date')
            ORDER BY column_name
        """)
        
        print("\n📊 РЕЗУЛЬТАТ МИГРАЦИИ:")
        for row in cursor.fetchall():
            column_name, data_type, is_nullable, default_value = row
            print(f"   {column_name}: {data_type} (nullable: {is_nullable}, default: {default_value})")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("🚀 Система рассылок полностью готова к работе")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Установите: pip install psycopg2-binary")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        logger.error(f"Migration error: {e}")
        return False

def show_manual_migration_info():
    """Показывает информацию для ручной миграции"""
    print("\n" + "=" * 60)
    print("📖 РУЧНАЯ МИГРАЦИЯ (если автоматическая не сработала)")
    print("=" * 60)
    print("Выполните эти SQL команды в вашей PostgreSQL базе данных:")
    print()
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_rewarded BOOLEAN DEFAULT false;")
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_rewarded_date TIMESTAMP;")
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked BOOLEAN DEFAULT false;")
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS block_date TIMESTAMP;")
    print()
    print("=" * 60)

if __name__ == "__main__":
    print("PostgreSQL Migration for Broadcast System")
    print("=" * 40)
    
    success = run_migration()
    
    if not success:
        show_manual_migration_info()
    
    print(f"\n{'✅ SUCCESS' if success else '⚠️  CHECK REQUIRED'}")
