#!/usr/bin/env python3
# test_export.py - Создание тестовых записей и проверка экспорта

import sqlite3
import datetime
import sys
import os

def create_test_users():
    """Создает тестовых пользователей в SQLite базе данных."""
    
    # Используем путь к локальной базе данных
    db_path = '/workspaces/evgenich-gift/bot_database.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Проверяем существует ли таблица users
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cur.fetchone():
            print("❌ Таблица users не найдена. Создаем структуру...")
            
            # Создаем таблицу users
            cur.execute('''
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    phone_number TEXT,
                    signup_date TEXT,
                    contact_shared_date TEXT,
                    real_name TEXT,
                    birth_date TEXT,
                    profile_completed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'registered',
                    source TEXT DEFAULT 'telegram',
                    referrer_id INTEGER,
                    brought_by_staff_id INTEGER,
                    redeem_date TEXT
                )
            ''')
            print("✅ Таблица users создана.")
        
        # Проверяем существует ли таблица staff
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staff'")
        if not cur.fetchone():
            print("❌ Таблица staff не найдена. Создаем...")
            cur.execute('''
                CREATE TABLE staff (
                    staff_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    short_name TEXT,
                    position TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Добавляем тестового сотрудника
            cur.execute('''
                INSERT INTO staff (staff_id, full_name, short_name, position, status)
                VALUES (1, 'Иван Петров', 'Иван П.', 'Официант', 'active')
            ''')
            print("✅ Таблица staff создана с тестовым сотрудником.")
        
        # Создаем тестовых пользователей
        test_users = [
            {
                'user_id': 111111,
                'first_name': 'Тест Юзер',
                'username': 'test_user_1',
                'phone_number': '+7900123456',
                'signup_date': datetime.datetime.now().isoformat(),
                'contact_shared_date': datetime.datetime.now().isoformat(),
                'real_name': 'Тестов Тест Тестович',
                'birth_date': '1990-01-01',
                'profile_completed': 1,
                'status': 'registered',
                'source': 'telegram',
                'referrer_id': None,
                'brought_by_staff_id': None,
                'redeem_date': None
            },
            {
                'user_id': 222222,
                'first_name': 'Анна',
                'username': 'anna_test',
                'phone_number': '+7900123457',
                'signup_date': (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
                'contact_shared_date': (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
                'real_name': 'Анна Смирнова',
                'birth_date': '1995-05-15',
                'profile_completed': 1,
                'status': 'redeemed',
                'source': 'staff',
                'referrer_id': None,
                'brought_by_staff_id': 1,
                'redeem_date': datetime.datetime.now().isoformat()
            },
            {
                'user_id': 333333,
                'first_name': 'Петр',
                'username': 'petr_referral',
                'phone_number': '+7900123458',
                'signup_date': (datetime.datetime.now() - datetime.timedelta(hours=12)).isoformat(),
                'contact_shared_date': (datetime.datetime.now() - datetime.timedelta(hours=12)).isoformat(),
                'real_name': 'Петр Иванов',
                'birth_date': '1988-12-20',
                'profile_completed': 1,
                'status': 'registered',
                'source': 'referral',
                'referrer_id': 111111,
                'brought_by_staff_id': None,
                'redeem_date': None
            }
        ]
        
        # Вставляем тестовых пользователей
        for user in test_users:
            try:
                cur.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, first_name, username, phone_number, signup_date, 
                     contact_shared_date, real_name, birth_date, profile_completed, 
                     status, source, referrer_id, brought_by_staff_id, redeem_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user['user_id'], user['first_name'], user['username'], 
                    user['phone_number'], user['signup_date'], user['contact_shared_date'],
                    user['real_name'], user['birth_date'], user['profile_completed'],
                    user['status'], user['source'], user['referrer_id'],
                    user['brought_by_staff_id'], user['redeem_date']
                ))
                print(f"✅ Добавлен тестовый пользователь: {user['first_name']} (ID: {user['user_id']})")
            except sqlite3.Error as e:
                print(f"❌ Ошибка при добавлении пользователя {user['first_name']}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 Тестовые данные созданы в базе: {db_path}")
        
        # Проверяем количество записей
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        conn.close()
        
        print(f"📊 Всего пользователей в базе: {count}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании тестовых данных: {e}")
        return False

def test_export():
    """Тестирует функцию экспорта."""
    print("\n🚀 Для тестирования экспорта:")
    print("1. Зайдите в Telegram бот")
    print("2. Откройте админку (/admin)")
    print("3. Выберите: 💾 Управление данными → 📥 Выгрузить в Google Sheets")
    print("4. Проверьте результат в боте")
    return True

if __name__ == '__main__':
    print("🧪 Создание тестовых данных для проверки экспорта в Google Sheets\n")
    
    # Создаем тестовые записи
    if create_test_users():
        print("\n" + "="*50)
        # Тестируем экспорт (будет работать только на Railway с настроенными переменными)
        test_export()
        
        print("\n📋 Инструкции для проверки:")
        print("1. Зайдите в Telegram бот")
        print("2. Откройте админку (/admin)")
        print("3. Выберите: 💾 Управление данными → 📥 Выгрузить в Google Sheets")
        print("4. Проверьте таблицу: https://docs.google.com/spreadsheets/d/1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs/edit")
        print("5. В листе 'Выгрузка Пользователей' должны появиться 3 тестовых пользователя")
    else:
        print("❌ Не удалось создать тестовые данные")
