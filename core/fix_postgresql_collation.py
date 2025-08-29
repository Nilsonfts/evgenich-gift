#!/usr/bin/env python3
"""
Скрипт для исправления предупреждений PostgreSQL о несоответствии версий collation.
Выполняет команду ALTER DATABASE railway REFRESH COLLATION VERSION.
"""
import os
import sys
import logging
import psycopg2
from psycopg2 import sql

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import POSTGRES_URL

def fix_collation_version():
    """Исправляет предупреждения о версии collation в PostgreSQL."""
    try:
        # Подключаемся к PostgreSQL
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("🔧 Исправляем версию collation в PostgreSQL...")
        
        # Выполняем команду обновления collation
        cur.execute("ALTER DATABASE railway REFRESH COLLATION VERSION;")
        
        print("✅ Версия collation успешно обновлена!")
        
        # Проверяем статус
        cur.execute("SELECT datname, datcollate, datctype FROM pg_database WHERE datname = 'railway';")
        result = cur.fetchone()
        if result:
            print(f"📊 База данных: {result[0]}")
            print(f"📊 Collation: {result[1]}")
            print(f"📊 CType: {result[2]}")
        
        cur.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Ошибка PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск исправления PostgreSQL collation...")
    success = fix_collation_version()
    if success:
        print("🎉 Исправление завершено успешно!")
        sys.exit(0)
    else:
        print("💥 Исправление не удалось!")
        sys.exit(1)
