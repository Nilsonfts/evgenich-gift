#!/usr/bin/env python3
import sqlite3
import os
from config import DATABASE_PATH

print("🔍 Проверка базы данных...")

db_path = DATABASE_PATH

if not os.path.exists(db_path):
    print(f"❌ База данных не найдена: {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Проверяем таблицы
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print(f"📋 Таблицы в базе: {[t[0] for t in tables]}")
    
    # Проверяем пользователей
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    print(f"👥 Всего пользователей: {user_count}")
    
    if user_count > 0:
        # Проверяем источники
        cur.execute("SELECT source, COUNT(*) FROM users GROUP BY source ORDER BY COUNT(*) DESC")
        sources = cur.fetchall()
        print("📊 Источники трафика:")
        for source, count in sources:
            print(f"   • {source}: {count}")
    
    conn.close()
    print("✅ Проверка завершена")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
