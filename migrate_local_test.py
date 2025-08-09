#!/usr/bin/env python3
"""
Тестовая миграция для проверки структуры PostgreSQL схемы
"""

import sys
import os
from db.postgres_client import PostgreSQLClient
from config import USE_POSTGRES, DATABASE_URL, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

def test_postgres_migration():
    """Тестируем подключение к PostgreSQL и проверяем схему"""
    
    if not USE_POSTGRES:
        print("❌ PostgreSQL не используется в конфигурации")
        return False
    
    try:
        # Пытаемся создать PostgreSQL клиент
        postgres_client = PostgreSQLClient()
        
        print("✅ PostgreSQL клиент создан успешно")
        print(f"📊 Схема таблицы users содержит колонки:")
        
        # Выводим информацию о колонках таблицы users
        for column in postgres_client.users_table.columns:
            print(f"   - {column.name}: {column.type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка PostgreSQL: {e}")
        print("💡 Это нормально в dev среде без реального PostgreSQL сервера")
        return False

def show_migration_info():
    """Показываем информацию о необходимой миграции"""
    
    print("=" * 60)
    print("🔄 ИНФОРМАЦИЯ О МИГРАЦИИ POSTGRESQL")
    print("=" * 60)
    print()
    print("📋 Необходимо добавить следующие колонки в таблицу users:")
    print("   - referrer_rewarded (BOOLEAN, default=false)")
    print("   - referrer_rewarded_date (TIMESTAMP, nullable)")
    print("   - blocked (BOOLEAN, default=false)")
    print("   - block_date (TIMESTAMP, nullable)")
    print()
    print("💻 SQL команды для выполнения в production:")
    print()
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_rewarded BOOLEAN DEFAULT false;")
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_rewarded_date TIMESTAMP;")
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked BOOLEAN DEFAULT false;")
    print("ALTER TABLE users ADD COLUMN IF NOT EXISTS block_date TIMESTAMP;")
    print()
    print("🚀 После применения миграции система рассылок будет полностью готова!")
    print("=" * 60)

if __name__ == "__main__":
    print("🔍 ПРОВЕРКА СИСТЕМЫ РАССЫЛОК И POSTGRESQL")
    print("=" * 50)
    
    # Тестируем PostgreSQL подключение
    postgres_works = test_postgres_migration()
    
    if not postgres_works:
        print("\n📚 В среде разработки PostgreSQL может быть недоступен")
    
    # Показываем информацию о миграции
    show_migration_info()
    
    print("\n✅ Проверка завершена")
