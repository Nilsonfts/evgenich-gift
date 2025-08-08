#!/usr/bin/env python3
"""
Скрипт для проверки и инициализации базы данных без зависимостей от config
"""

import sqlite3
import os
from datetime import datetime
import pytz

# Путь к базе данных
DB_PATH = "data/evgenich_data.db"

def init_db():
    """Инициализирует базу данных со всеми необходимыми таблицами"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            birthday TEXT,
            signup_date TEXT,
            redeem_date TEXT,
            status TEXT DEFAULT 'registered',
            source TEXT DEFAULT 'direct',
            staff_member TEXT,
            visit_time INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица персонала
    cur.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Таблица данных iiko
    cur.execute('''
        CREATE TABLE IF NOT EXISTS iiko_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            nastoika_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица истории разговоров
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована!")

def check_database():
    """Проверяет состояние базы данных"""
    print("🔍 Проверка состояния базы данных...")
    print(f"📁 Путь к БД: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ База данных не существует!")
        return
    
    file_size = os.path.getsize(DB_PATH)
    print(f"📊 Размер файла БД: {file_size} байт")
    
    if file_size == 0:
        print("⚠️  База данных пуста - требуется инициализация")
        return
    
    # Подключаемся к базе
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Проверяем таблицы
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"📋 Найденные таблицы: {tables}")
    
    if 'users' in tables:
        # Проверяем данные пользователей
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        print(f"👥 Всего пользователей: {total_users}")
        
        if total_users > 0:
            # Последние записи
            cur.execute("SELECT user_id, signup_date, status, source FROM users ORDER BY signup_date DESC LIMIT 3")
            print("📋 Последние пользователи:")
            for row in cur.fetchall():
                print(f"  ID: {row['user_id']}, Дата: {row['signup_date']}, Статус: {row['status']}, Источник: {row['source']}")
            
            # Проверяем данные за сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            cur.execute("SELECT COUNT(*) FROM users WHERE date(signup_date) = ?", (today,))
            today_users = cur.fetchone()[0]
            print(f"📅 Пользователей за сегодня ({today}): {today_users}")
    
    if 'staff' in tables:
        cur.execute("SELECT COUNT(*) FROM staff")
        staff_count = cur.fetchone()[0]
        print(f"👨‍💼 Сотрудников в базе: {staff_count}")
    
    conn.close()

def test_report_period():
    """Тестирует период отчета"""
    print("\n🔍 Тестирование периода отчета (08.08 12:00 - 16:44)...")
    
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        print("❌ База данных не инициализирована")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Проверяем период
    start_time = "2025-08-08 12:00:00"
    end_time = "2025-08-08 16:44:00"
    
    cur.execute("SELECT COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? AND status IN ('issued', 'redeemed', 'redeemed_and_left')", (start_time, end_time))
    issued = cur.fetchone()[0]
    print(f"🎫 Выдано подарков: {issued}")
    
    cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ?", (start_time, end_time))
    redeemed = cur.fetchone()[0]
    print(f"🎁 Активировано подарков: {redeemed}")
    
    # Проверяем источники
    cur.execute("SELECT source, COUNT(*) as count FROM users WHERE signup_date BETWEEN ? AND ? GROUP BY source", (start_time, end_time))
    sources = cur.fetchall()
    if sources:
        print("📊 Источники:")
        for row in sources:
            print(f"  {row['source']}: {row['count']}")
    else:
        print("📊 Нет данных по источникам за период")
    
    conn.close()

if __name__ == "__main__":
    check_database()
    
    # Если база пуста, инициализируем
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        init_db()
        print("🔄 База данных была инициализирована")
        check_database()
    
    test_report_period()
