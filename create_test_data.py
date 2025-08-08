#!/usr/bin/env python3
"""
Создает тестовые данные для проверки отчетов
"""

import sqlite3
from datetime import datetime, timedelta
import random

# Путь к базе данных
DB_PATH = "data/evgenich_data.db"

def create_test_data():
    """Создает тестовые данные для проверки отчетов"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("🔧 Создаем тестовые данные...")
    
    # Сегодня
    today = datetime.now()
    
    # Создаем данные для периода 08.08 12:00 - 16:44
    test_period_start = datetime(2025, 8, 8, 12, 0, 0)
    test_period_end = datetime(2025, 8, 8, 16, 44, 0)
    
    # Источники трафика
    sources = [
        "qr_table", "qr_bar", "qr_wc", "qr_entrance", 
        "instagram", "telegram", "whatsapp", "direct",
        "staff", "recommendation"
    ]
    
    # Статусы
    statuses = ["issued", "redeemed", "redeemed_and_left"]
    
    # Создаем тестовых пользователей
    test_users = []
    
    # 15 пользователей в тестовый период
    for i in range(15):
        user_id = 100000 + i
        signup_time = test_period_start + timedelta(
            minutes=random.randint(0, int((test_period_end - test_period_start).total_seconds() / 60))
        )
        
        # Некоторые активировали подарки
        redeem_time = None
        status = random.choice(statuses)
        if status in ["redeemed", "redeemed_and_left"]:
            redeem_time = signup_time + timedelta(hours=random.randint(1, 3))
        else:
            status = "issued"
        
        source = random.choice(sources)
        
        test_user = {
            'user_id': user_id,
            'username': f'testuser{i}',
            'first_name': f'Тест{i}',
            'last_name': f'Пользователь{i}',
            'signup_date': signup_time.isoformat(),
            'redeem_date': redeem_time.isoformat() if redeem_time else None,
            'status': status,
            'source': source
        }
        test_users.append(test_user)
    
    # Добавляем еще данных за сегодня (но вне тестового периода)
    for i in range(10):
        user_id = 200000 + i
        # Данные за сегодня, но не в период 12:00-16:44
        if random.choice([True, False]):
            # Утренние данные
            signup_time = today.replace(hour=random.randint(8, 11), minute=random.randint(0, 59))
        else:
            # Вечерние данные
            signup_time = today.replace(hour=random.randint(17, 22), minute=random.randint(0, 59))
        
        status = random.choice(statuses)
        redeem_time = None
        if status in ["redeemed", "redeemed_and_left"]:
            redeem_time = signup_time + timedelta(hours=random.randint(1, 4))
        else:
            status = "issued"
        
        source = random.choice(sources)
        
        test_user = {
            'user_id': user_id,
            'username': f'todayuser{i}',
            'first_name': f'Сегодня{i}',
            'last_name': f'Пользователь{i}',
            'signup_date': signup_time.isoformat(),
            'redeem_date': redeem_time.isoformat() if redeem_time else None,
            'status': status,
            'source': source
        }
        test_users.append(test_user)
    
    # Вставляем данные в базу
    for user in test_users:
        cur.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, signup_date, redeem_date, status, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['user_id'], user['username'], user['first_name'], user['last_name'],
            user['signup_date'], user['redeem_date'], user['status'], user['source']
        ))
    
    # Создаем тестовых сотрудников
    staff_members = [
        ("Анна Менеджерова", "Менеджер"),
        ("Петр Официантов", "Официант"),
        ("Мария Барменова", "Бармен"),
        ("Иван Поваров", "Повар")
    ]
    
    for name, position in staff_members:
        cur.execute('''
            INSERT OR IGNORE INTO staff (name, position, is_active)
            VALUES (?, ?, 1)
        ''', (name, position))
    
    # Добавляем данные iiko за сегодня
    cur.execute('''
        INSERT OR REPLACE INTO iiko_data (date, nastoika_count)
        VALUES (?, ?)
    ''', (today.strftime('%Y-%m-%d'), random.randint(50, 100)))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Создано {len(test_users)} тестовых пользователей")
    print(f"✅ Создано {len(staff_members)} тестовых сотрудников")
    print("✅ Добавлены данные iiko")

def show_test_data():
    """Показывает созданные тестовые данные"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("\n📊 Анализ тестовых данных:")
    
    # Всего пользователей
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    print(f"👥 Всего пользователей: {total}")
    
    # За тестовый период
    test_start = "2025-08-08 12:00:00"
    test_end = "2025-08-08 16:44:00"
    
    cur.execute('''
        SELECT COUNT(*) FROM users 
        WHERE signup_date BETWEEN ? AND ? 
        AND status IN ('issued', 'redeemed', 'redeemed_and_left')
    ''', (test_start, test_end))
    test_period_issued = cur.fetchone()[0]
    
    cur.execute('''
        SELECT COUNT(*) FROM users 
        WHERE redeem_date BETWEEN ? AND ?
    ''', (test_start, test_end))
    test_period_redeemed = cur.fetchone()[0]
    
    print(f"🎫 В тестовый период (12:00-16:44) выдано: {test_period_issued}")
    print(f"🎁 В тестовый период активировано: {test_period_redeemed}")
    
    # Источники в тестовый период
    cur.execute('''
        SELECT source, COUNT(*) as count 
        FROM users 
        WHERE signup_date BETWEEN ? AND ? 
        GROUP BY source
        ORDER BY count DESC
    ''', (test_start, test_end))
    
    sources = cur.fetchall()
    if sources:
        print("📊 Источники в тестовый период:")
        for row in sources:
            print(f"  {row['source']}: {row['count']}")
    
    # За сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM users WHERE date(signup_date) = ?", (today,))
    today_total = cur.fetchone()[0]
    print(f"📅 За сегодня всего: {today_total}")
    
    conn.close()

if __name__ == "__main__":
    create_test_data()
    show_test_data()
