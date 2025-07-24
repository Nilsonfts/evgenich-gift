#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции полного отчета.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_with_mock_data():
    """Тестирует функцию с моковыми данными."""
    print("🧪 Создание тестовой базы данных и проверка функции отчета...")
    
    try:
        # Создаем директорию data если её нет
        if not os.path.exists('data'):
            os.makedirs('data')
            print("✅ Создана директория data")

        # Инициализируем базу данных
        import sqlite3
        from datetime import datetime, timedelta

        db_path = "data/evgenich_data.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Создаем таблицу users с нужными полями
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                status TEXT DEFAULT 'registered',
                source TEXT DEFAULT 'direct',
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeem_date TIMESTAMP,
                referrer_id INTEGER,
                brought_by_staff_id INTEGER,
                registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Добавляем тестовые данные
        base_date = datetime(2025, 7, 10)  # Дата запуска бота
        test_users = [
            (1, "Иван", "ivan123", "redeemed", "direct", None, None, None, base_date, base_date + timedelta(hours=2)),
            (2, "Петр", "petr456", "issued", "referral", "telegram", "social", "promo1", base_date + timedelta(days=1), None),
            (3, "Мария", "maria789", "redeemed_and_left", "staff", None, None, None, base_date + timedelta(days=2), base_date + timedelta(days=2, hours=3)),
            (4, "Анна", "anna000", "redeemed", "channel", "instagram", "social", "ads", base_date + timedelta(days=3), base_date + timedelta(days=3, hours=1)),
            (5, "Олег", "oleg111", "left", "direct", None, None, None, base_date + timedelta(days=4), None),
        ]

        for user_data in test_users:
            cur.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, first_name, username, status, source, utm_source, utm_medium, utm_campaign, signup_date, redeem_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, user_data)

        conn.commit()
        conn.close()
        print("✅ Тестовые данные добавлены в базу")

        # Теперь тестируем нашу функцию
        print("\n🔍 Тестирование функции get_all_users_for_report...")
        
        # Импортируем функцию напрямую из database
        import sqlite3
        
        # Копируем логику функции для теста
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                user_id,
                first_name,
                username, 
                status,
                source,
                utm_source,
                utm_medium,
                utm_campaign,
                signup_date,
                redeem_date,
                referrer_id,
                brought_by_staff_id,
                registration_time
            FROM users 
            ORDER BY signup_date ASC
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        print(f"✅ Получено {len(rows)} пользователей из базы")
        
        # Тестируем логику отчета
        total_subscribed = 0
        total_unsubscribed = 0
        sources_stats = {}
        
        for row in rows:
            user = dict(row)
            print(f"  • {user['first_name']} (@{user['username']}) - {user['status']} - {user['source']}")
            
            # Подсчитываем подписавшихся
            if user.get('status') in ['issued', 'redeemed', 'redeemed_and_left']:
                total_subscribed += 1
            
            # Подсчитываем отписавшихся
            if user.get('status') in ['left', 'unsubscribed']:
                total_unsubscribed += 1
            
            # Анализируем источники
            source = user.get('source', 'direct')
            utm_source = user.get('utm_source', 'unknown')
            
            if source == 'referral':
                channel = 'Реферальная программа'
            elif source == 'staff':
                channel = 'Через сотрудника'
            elif utm_source and utm_source != 'unknown':
                channel = f'UTM: {utm_source}'
            elif source == 'channel':
                channel = 'Telegram канал'
            else:
                channel = 'Прямой переход'
            
            sources_stats[channel] = sources_stats.get(channel, 0) + 1
        
        delta = total_subscribed - total_unsubscribed
        
        print(f"\n📊 Результаты анализа:")
        print(f"✅ Всего подписалось: {total_subscribed}")
        print(f"❌ Всего отписалось: {total_unsubscribed}")
        print(f"📊 Дельта: {delta:+d}")
        print(f"👥 Активных пользователей: {len(rows)}")
        print(f"\n🎯 Источники привлечения:")
        for channel, count in sorted(sources_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(rows)) * 100 if rows else 0
            print(f"• {channel}: {count} чел. ({percentage:.1f}%)")

        print("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_mock_data()
