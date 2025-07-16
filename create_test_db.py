#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание тестовой базы данных для проверки системы QR-кодов
"""

import sqlite3
import datetime
import random
import string

def create_test_database():
    """Создает тестовую базу данных с примерами данных."""
    print("🔨 Создание тестовой базы данных...")
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Создаем таблицу staff
    cur.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            unique_code TEXT NOT NULL UNIQUE,
            position TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            telegram_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем таблицу users
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            status TEXT DEFAULT 'registered',
            source TEXT,
            referrer_id INTEGER,
            brought_by_staff_id INTEGER,
            signup_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            redeem_date DATETIME,
            FOREIGN KEY (brought_by_staff_id) REFERENCES staff (staff_id)
        )
    ''')
    
    print("✅ Таблицы созданы")
    
    # Добавляем тестовых сотрудников
    test_staff = [
        ("Иван Петров", "Иван П.", "IVAN2024", "Официант"),
        ("Мария Сидорова", "Мария С.", "MARIA2024", "Бармен"),
        ("Алексей Козлов", "Алексей К.", "ALEX2024", "Менеджер"),
        ("Елена Волкова", "Елена В.", "ELENA2024", "Официант"),
    ]
    
    for full_name, short_name, code, position in test_staff:
        try:
            cur.execute('''
                INSERT OR IGNORE INTO staff (full_name, short_name, unique_code, position, status)
                VALUES (?, ?, ?, ?, 'active')
            ''', (full_name, short_name, code, position))
            print(f"  ➕ Добавлен сотрудник: {full_name} (код: {code})")
        except sqlite3.IntegrityError:
            print(f"  ⚠️  Сотрудник {full_name} уже существует")
    
    # Добавляем тестовых пользователей
    print("\n📱 Добавление тестовых пользователей...")
    
    # Получаем ID сотрудников для тестовых данных
    cur.execute("SELECT staff_id, short_name FROM staff WHERE status = 'active'")
    staff_list = cur.fetchall()
    
    current_time = datetime.datetime.now()
    
    # Создаем тестовых пользователей за последние 7 дней
    for day in range(7):
        signup_date = current_time - datetime.timedelta(days=day)
        
        # Пользователи от разных источников
        test_users = [
            # Прямые переходы
            (100000 + day * 10 + 1, f"user{day}1", "Тест1", "direct", None, None),
            (100000 + day * 10 + 2, f"user{day}2", "Тест2", "qr_bar", None, None),
            
            # Переходы по QR-кодам сотрудников (если есть сотрудники)
        ]
        
        if staff_list:
            # Добавляем переходы по QR-кодам сотрудников
            for i, staff in enumerate(staff_list):
                if random.random() < 0.7:  # 70% вероятность перехода
                    user_id = 100000 + day * 10 + 10 + i
                    source = f"Сотрудник: {staff['short_name']}"
                    test_users.append((
                        user_id, 
                        f"staff_user{day}{i}", 
                        f"Гость{i}", 
                        source, 
                        None, 
                        staff['staff_id']
                    ))
        
        for user_id, username, first_name, source, referrer_id, brought_by_staff_id in test_users:
            try:
                cur.execute('''
                    INSERT OR IGNORE INTO users 
                    (user_id, username, first_name, status, source, referrer_id, brought_by_staff_id, signup_date)
                    VALUES (?, ?, ?, 'issued', ?, ?, ?, ?)
                ''', (user_id, username, first_name, source, referrer_id, brought_by_staff_id, signup_date))
                
                print(f"  ➕ День {day}: пользователь {username} (источник: {source})")
            except sqlite3.IntegrityError:
                pass  # Пользователь уже существует
    
    # Добавляем несколько примеров с некорректными кодами сотрудников
    print("\n❌ Добавление примеров с некорректными кодами...")
    
    invalid_examples = [
        (200001, "bad_user1", "Ошибка1", "Неизвестный_сотрудник_WRONG123"),
        (200002, "bad_user2", "Ошибка2", "Неизвестный_сотрудник_FAKE456"),
    ]
    
    for user_id, username, first_name, source in invalid_examples:
        try:
            cur.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, status, source, signup_date)
                VALUES (?, ?, ?, 'registered', ?, ?)
            ''', (user_id, username, first_name, source, current_time))
            print(f"  ➕ Некорректный переход: {username} (источник: {source})")
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()
    
    print("\n✅ Тестовая база данных создана!")
    print("\n🎯 Что добавлено:")
    print("  • 4 тестовых сотрудника с QR-кодами")
    print("  • Пользователи от разных источников за 7 дней")
    print("  • Примеры успешных переходов по QR-кодам")
    print("  • Примеры некорректных QR-кодов")
    
    return True

def show_qr_codes():
    """Показывает QR-коды всех сотрудников."""
    print("\n🔗 QR-КОДЫ СОТРУДНИКОВ:")
    print("=" * 50)
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM staff WHERE status = 'active'")
    staff_list = cur.fetchall()
    
    for staff in staff_list:
        qr_url = f"https://t.me/EvgenichTapBarBot?start=w_{staff['unique_code']}"
        print(f"👤 {staff['full_name']} ({staff['position']})")
        print(f"   Код: {staff['unique_code']}")
        print(f"   QR-ссылка: {qr_url}")
        print()
    
    conn.close()

if __name__ == "__main__":
    print("🧪 СОЗДАНИЕ ТЕСТОВОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    create_test_database()
    show_qr_codes()
    
    print("💡 Теперь можно запустить диагностику:")
    print("   python simple_qr_test.py")
    print("=" * 50)
