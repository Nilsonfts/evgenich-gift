#!/usr/bin/env python3
"""
Тест простых QR-кодов по Telegram ID
"""

import sqlite3
import os
from datetime import datetime, timedelta

def test_simple_qr_codes():
    """Тестирует QR-коды с простыми кодами (Telegram ID)."""
    
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    print("🧪 ТЕСТ ПРОСТЫХ QR-КОДОВ")
    print("=" * 30)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Тестовые коды
    test_codes = [
        "208281210",  # Кристина
        "196614680",  # Нил
        "TEST2024"    # Тестовый
    ]
    
    print("🔍 Проверяем коды сотрудников:")
    for code in test_codes:
        cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (code,))
        staff = cur.fetchone()
        
        if staff:
            print(f"✅ Код '{code}' → {staff['full_name']} ({staff['position']})")
        else:
            print(f"❌ Код '{code}' не найден!")
    
    # Симулируем переход по QR-коду Кристины
    print(f"\n📱 Симулируем переход по QR-коду Кристины:")
    print(f"🔗 https://t.me/evgenichspbbot?start=w_208281210")
    
    # Удаляем тестовых пользователей
    cur.execute("DELETE FROM users WHERE user_id >= 800000000")
    
    # Добавляем тестового пользователя через код Кристины
    test_user_id = 800000001
    staff_code = "208281210"
    
    # Находим сотрудника
    cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (staff_code,))
    staff_member = cur.fetchone()
    
    if staff_member:
        try:
            cur.execute("""
                INSERT INTO users 
                (user_id, username, first_name, source, brought_by_staff_id, status, registration_time)
                VALUES (?, ?, ?, 'staff', ?, 'issued', datetime('now'))
            """, (
                test_user_id,
                "testuser_kristina",
                "Тестовый Гость Кристины",
                staff_member['staff_id']
            ))
            
            conn.commit()
            print(f"✅ Гость успешно привязан к сотруднику: {staff_member['full_name']}")
            
        except Exception as e:
            print(f"❌ Ошибка добавления: {e}")
    
    # Проверяем статистику
    print(f"\n📊 Статистика по источникам:")
    cur.execute("""
        SELECT source, COUNT(*) as count 
        FROM users 
        WHERE user_id >= 800000000
        GROUP BY source 
        ORDER BY count DESC
    """)
    
    sources = cur.fetchall()
    for source in sources:
        print(f"• {source['source']}: {source['count']} переходов")
    
    # Статистика по сотрудникам
    print(f"\n👥 Статистика по сотрудникам (последние переходы):")
    cur.execute("""
        SELECT 
            s.full_name,
            s.unique_code,
            COUNT(u.user_id) as attracted_users
        FROM staff s
        LEFT JOIN users u ON s.staff_id = u.brought_by_staff_id 
            AND u.source = 'staff'
            AND u.user_id >= 800000000
        WHERE s.status = 'active'
        GROUP BY s.staff_id, s.full_name, s.unique_code
        ORDER BY attracted_users DESC
    """)
    
    staff_stats = cur.fetchall()
    for staff in staff_stats:
        qr_url = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
        print(f"• {staff['full_name']}: {staff['attracted_users']} гостей")
        print(f"  QR: {qr_url}")
        print()
    
    conn.close()
    print("🎉 Тест завершен!")

if __name__ == "__main__":
    test_simple_qr_codes()
