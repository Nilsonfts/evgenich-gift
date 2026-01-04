#!/usr/bin/env python3
"""Проверить структуру таблицы users."""
import psycopg2
import os
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL не установлена")
    exit(1)

try:
    parsed = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/')
    )
    cur = conn.cursor()
    
    print("📋 СТРУКТУРА ТАБЛИЦЫ 'users':")
    print("=" * 70)
    
    # Получим информацию о колонках
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'users'
        ORDER BY ordinal_position
    """)
    
    columns = cur.fetchall()
    
    if columns:
        print(f"\nКолонок в таблице: {len(columns)}\n")
        for col_name, data_type, is_nullable in columns:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"   {col_name:20} | {data_type:20} | {nullable}")
    else:
        print("❌ Таблица users не найдена!")
    
    # Проверим, какие есть таблицы вообще
    print("\n" + "=" * 70)
    print("📊 ВСЕ ТАБЛИЦЫ В БД:")
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    if tables:
        for (table_name,) in tables:
            print(f"   - {table_name}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
