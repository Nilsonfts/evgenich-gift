#!/usr/bin/env python3
"""
Симуляция полного процесса QR-кода: от регистрации сотрудника до перехода гостя
"""

import sqlite3
import os
import logging
from datetime import datetime

# Настройка логирования как в реальном боте
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def simulate_staff_registration():
    """Симулирует регистрацию нового сотрудника."""
    print("👤 СИМУЛЯЦИЯ РЕГИСТРАЦИИ СОТРУДНИКА")
    print("=" * 50)
    
    # Параметры тестового сотрудника
    telegram_id = 999999999  # Тестовый ID
    full_name = "Тест Сотрудников"
    position = "Тестер"
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Создаем короткое имя
    parts = full_name.split()
    short_name = f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]
    
    # Генерируем уникальный код
    base_code = parts[0].lower().strip().replace(' ', '')
    unique_code = f"{base_code.upper()}2024"
    
    print(f"📝 Регистрируем сотрудника:")
    print(f"   Telegram ID: {telegram_id}")
    print(f"   Полное имя: {full_name}")
    print(f"   Короткое имя: {short_name}")
    print(f"   Должность: {position}")
    print(f"   Уникальный код: {unique_code}")
    
    # Проверяем, есть ли уже такой сотрудник
    cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (telegram_id,))
    existing = cur.fetchone()
    
    if existing:
        print(f"   ⚠️ Сотрудник уже существует, обновляем...")
        cur.execute("""
            UPDATE staff 
            SET full_name = ?, short_name = ?, position = ?, status = 'active'
            WHERE telegram_id = ?
        """, (full_name, short_name, position, telegram_id))
    else:
        print(f"   ✅ Добавляем нового сотрудника...")
        cur.execute("""
            INSERT INTO staff (telegram_id, full_name, short_name, unique_code, position, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (telegram_id, full_name, short_name, unique_code, position))
    
    conn.commit()
    
    # Получаем данные созданного сотрудника
    cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (telegram_id,))
    staff_member = cur.fetchone()
    
    if staff_member:
        print(f"   🎉 Сотрудник успешно зарегистрирован!")
        print(f"   🔑 ID в базе: {staff_member['staff_id']}")
        print(f"   📱 QR-ссылка: https://t.me/EvgenichTapBarBot?start=w_{staff_member['unique_code']}")
        
        conn.close()
        return staff_member['unique_code']
    else:
        print(f"   ❌ Ошибка регистрации!")
        conn.close()
        return None

def simulate_guest_transition(staff_code):
    """Симулирует переход гостя по QR-коду сотрудника."""
    print(f"\n👥 СИМУЛЯЦИЯ ПЕРЕХОДА ГОСТЯ")
    print("=" * 50)
    
    # Параметры тестового гостя
    user_id = 888888888
    username = "test_guest"
    first_name = "Тестовый Гость"
    
    # Симулируем payload от QR-кода
    payload = f"w_{staff_code}"
    
    print(f"🔗 Гость переходит по ссылке:")
    print(f"   https://t.me/EvgenichTapBarBot?start={payload}")
    print(f"   User ID: {user_id}")
    print(f"   Username: @{username}")
    print()
    
    # Имитируем логику из user_commands.py
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Обрабатываем payload
    referrer_id = None
    brought_by_staff_id = None
    source = 'direct'
    
    if payload.startswith('w_'):
        staff_code_extracted = payload.replace('w_', '')
        logging.info(f"🔍 Попытка привязки к сотруднику с кодом: {staff_code_extracted} (пользователь: {user_id})")
        
        # Ищем сотрудника
        cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (staff_code_extracted,))
        staff_member = cur.fetchone()
        
        if staff_member:
            brought_by_staff_id = staff_member['staff_id']
            source = f"Сотрудник: {staff_member['short_name']}"
            logging.info(f"✅ Пользователь {user_id} (@{username}) успешно привязан к сотруднику: {staff_member['full_name']} (ID: {staff_member['staff_id']}, код: {staff_code_extracted})")
            
            print(f"✅ УСПЕШНАЯ ПРИВЯЗКА К СОТРУДНИКУ:")
            print(f"   Найден сотрудник: {staff_member['full_name']}")
            print(f"   ID сотрудника: {staff_member['staff_id']}")
            print(f"   Источник: {source}")
        else:
            logging.warning(f"❌ QR-код сотрудника некорректен! Код '{staff_code_extracted}' не найден в базе активных сотрудников. Переход засчитан как 'direct'.")
            source = 'direct'
            brought_by_staff_id = None
            
            print(f"❌ СОТРУДНИК НЕ НАЙДЕН:")
            print(f"   Код: {staff_code_extracted}")
            print(f"   Источник: {source}")
    
    # Проверяем, есть ли уже такой пользователь
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cur.fetchone()
    
    if existing_user:
        print(f"   ⚠️ Пользователь уже существует, не добавляем повторно")
    else:
        # Добавляем пользователя (имитируем add_new_user)
        try:
            cur.execute("""
                INSERT INTO users (user_id, username, first_name, source, referrer_id, brought_by_staff_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'registered', datetime('now'))
            """, (user_id, username, first_name, source, referrer_id, brought_by_staff_id))
            
            conn.commit()
            print(f"   ✅ Пользователь добавлен в базу")
            print(f"   📊 Источник в БД: {source}")
            print(f"   👤 brought_by_staff_id: {brought_by_staff_id}")
            
        except Exception as e:
            print(f"   ❌ Ошибка добавления пользователя: {e}")
    
    conn.close()

def check_results():
    """Проверяет результаты симуляции."""
    print(f"\n📊 ПРОВЕРКА РЕЗУЛЬТАТОВ")
    print("=" * 50)
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Проверяем последних пользователей
    cur.execute("""
        SELECT u.user_id, u.source, u.brought_by_staff_id, s.full_name as staff_name, u.created_at
        FROM users u
        LEFT JOIN staff s ON u.brought_by_staff_id = s.staff_id
        ORDER BY u.rowid DESC
        LIMIT 5
    """)
    
    recent_users = cur.fetchall()
    
    print("📋 Последние 5 пользователей:")
    for user in recent_users:
        if user['brought_by_staff_id']:
            print(f"   ✅ {user['user_id']}: {user['source']} → привел {user['staff_name']} (ID: {user['brought_by_staff_id']})")
        else:
            print(f"   ❌ {user['user_id']}: {user['source']} → без сотрудника")
    
    conn.close()

if __name__ == "__main__":
    print("🧪 ПОЛНАЯ СИМУЛЯЦИЯ ПРОЦЕССА QR-КОДА СОТРУДНИКА")
    print("=" * 60)
    
    # Шаг 1: Регистрация сотрудника
    staff_code = simulate_staff_registration()
    
    if staff_code:
        # Шаг 2: Переход гостя
        simulate_guest_transition(staff_code)
        
        # Шаг 3: Проверка результатов
        check_results()
    else:
        print("❌ Не удалось зарегистрировать сотрудника, тест прерван")
