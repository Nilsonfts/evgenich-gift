#!/usr/bin/env python3
"""
Инициализатор базы данных без зависимостей от config
"""

import sqlite3
import os

def init_correct_database():
    """Создает правильную базу данных в папке data."""
    
    # Создаем папку data
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    db_path = os.path.join(data_dir, "evgenich_data.db")
    
    print(f"🔧 Создаю базу данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Создаем таблицу staff
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            unique_code TEXT UNIQUE NOT NULL,
            position TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создаем таблицу users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            source TEXT DEFAULT 'direct',
            referrer_id INTEGER,
            brought_by_staff_id INTEGER,
            status TEXT DEFAULT 'registered',
            phone_number TEXT,
            real_name TEXT,
            birth_date TEXT,
            concept TEXT DEFAULT 'evgenich',
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brought_by_staff_id) REFERENCES staff(staff_id)
        )
    """)
    
    # Создаем остальные таблицы
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS newsletters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✅ База данных создана: {db_path}")
    return db_path

def add_test_staff(db_path):
    """Добавляет тестового сотрудника с правильным telegram_id."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Добавляем тестового сотрудника
    test_staff = {
        'telegram_id': 12345678,  # Тестовый telegram ID
        'full_name': 'Тест Сотрудникович',
        'short_name': 'Тест С.',
        'unique_code': 'TEST2024',
        'position': 'Тестер'
    }
    
    try:
        cur.execute("""
            INSERT OR REPLACE INTO staff (telegram_id, full_name, short_name, unique_code, position, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (
            test_staff['telegram_id'],
            test_staff['full_name'], 
            test_staff['short_name'],
            test_staff['unique_code'],
            test_staff['position']
        ))
        
        conn.commit()
        print(f"✅ Добавлен тестовый сотрудник:")
        print(f"   Telegram ID: {test_staff['telegram_id']}")
        print(f"   Имя: {test_staff['full_name']}")
        print(f"   Код: {test_staff['unique_code']}")
        print(f"   QR-ссылка: https://t.me/EvgenichTapBarBot?start=w_{test_staff['unique_code']}")
        
    except Exception as e:
        print(f"❌ Ошибка добавления сотрудника: {e}")
    
    conn.close()

def check_database(db_path):
    """Проверяет содержимое базы данных."""
    if not os.path.exists(db_path):
        print(f"❌ База данных не существует: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print(f"\n📊 СОДЕРЖИМОЕ БАЗЫ ДАННЫХ: {db_path}")
    print("=" * 50)
    
    # Проверяем сотрудников
    cur.execute("SELECT * FROM staff")
    staff = cur.fetchall()
    
    print(f"👥 Сотрудников в базе: {len(staff)}")
    for s in staff:
        print(f"  • {s['full_name']} (ID: {s['staff_id']}, Telegram: {s['telegram_id']}, Код: {s['unique_code']})")
    
    # Проверяем пользователей
    cur.execute("SELECT COUNT(*) as count FROM users")
    user_count = cur.fetchone()['count']
    print(f"\n👤 Пользователей в базе: {user_count}")
    
    if user_count > 0:
        cur.execute("SELECT user_id, source, brought_by_staff_id FROM users ORDER BY rowid DESC LIMIT 5")
        recent_users = cur.fetchall()
        print("  Последние 5 пользователей:")
        for u in recent_users:
            print(f"    - {u['user_id']}: {u['source']} (staff_id: {u['brought_by_staff_id']})")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 ИНИЦИАЛИЗАЦИЯ ПРАВИЛЬНОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Создаем БД
    db_path = init_correct_database()
    
    # Добавляем тестового сотрудника
    add_test_staff(db_path)
    
    # Проверяем результат
    check_database(db_path)
