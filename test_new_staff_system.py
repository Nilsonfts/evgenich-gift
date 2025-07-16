#!/usr/bin/env python3
"""
Тест новой системы QR-кодов с source = "staff"
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta

def test_new_staff_system():
    """Тестирует новую систему с source = 'staff'."""
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена! Запустите init_correct_db.py")
        return
    
    print("🧪 ТЕСТ НОВОЙ СИСТЕМЫ QR-КОДОВ С SOURCE = 'staff'")
    print("=" * 55)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Очищаем тестовые данные
    cur.execute("DELETE FROM users WHERE user_id >= 700000000")
    
    # Получаем существующих сотрудников
    cur.execute("SELECT * FROM staff WHERE status = 'active'")
    staff_members = cur.fetchall()
    
    print(f"👥 Активных сотрудников: {len(staff_members)}")
    
    # Симулируем переходы по QR-кодам разных сотрудников
    test_users = []
    
    for i, staff in enumerate(staff_members):
        # Создаем несколько пользователей для каждого сотрудника
        for j in range(3 + i):  # Разное количество для каждого
            user_id = 700000000 + i * 100 + j
            
            try:
                cur.execute("""
                    INSERT INTO users 
                    (user_id, username, first_name, source, brought_by_staff_id, status, registration_time)
                    VALUES (?, ?, ?, 'staff', ?, 'issued', datetime('now', '-' || ? || ' hours'))
                """, (
                    user_id,
                    f"testuser{i}_{j}",
                    f"Тестовый Пользователь {i}_{j}",
                    staff['staff_id'],
                    j  # Разное время
                ))
                
                test_users.append({
                    'user_id': user_id,
                    'staff_name': staff['full_name'],
                    'staff_code': staff['unique_code']
                })
                
            except Exception as e:
                print(f"❌ Ошибка добавления пользователя: {e}")
    
    # Добавляем несколько direct пользователей для сравнения
    for i in range(5):
        user_id = 799000000 + i
        try:
            cur.execute("""
                INSERT INTO users 
                (user_id, username, first_name, source, status, registration_time)
                VALUES (?, ?, ?, 'direct', 'issued', datetime('now', '-' || ? || ' hours'))
            """, (
                user_id,
                f"directuser{i}",
                f"Прямой Пользователь {i}",
                i
            ))
        except Exception as e:
            print(f"❌ Ошибка добавления direct пользователя: {e}")
    
    conn.commit()
    
    print(f"✅ Создано {len(test_users)} тестовых переходов по QR-кодам")
    print(f"✅ Создано 5 тестовых direct переходов")
    
    # Проверяем статистику по источникам
    print(f"\n📊 СТАТИСТИКА ПО ИСТОЧНИКАМ:")
    print("-" * 35)
    
    cur.execute("""
        SELECT source, COUNT(*) as count 
        FROM users 
        WHERE user_id >= 700000000
        GROUP BY source 
        ORDER BY count DESC
    """)
    
    sources = cur.fetchall()
    for source in sources:
        print(f"• {source['source']}: {source['count']} переходов")
    
    # Проверяем статистику по сотрудникам
    print(f"\n👥 СТАТИСТИКА ПО СОТРУДНИКАМ:")
    print("-" * 35)
    
    cur.execute("""
        SELECT 
            s.full_name,
            s.unique_code,
            COUNT(u.user_id) as attracted_users
        FROM staff s
        LEFT JOIN users u ON s.staff_id = u.brought_by_staff_id 
            AND u.source = 'staff'
            AND u.user_id >= 700000000
        WHERE s.status = 'active'
        GROUP BY s.staff_id, s.full_name, s.unique_code
        ORDER BY attracted_users DESC
    """)
    
    staff_stats = cur.fetchall()
    for staff in staff_stats:
        print(f"• {staff['full_name']} ({staff['unique_code']}): {staff['attracted_users']} гостей")
    
    # Тестируем функцию топа сотрудников
    print(f"\n🏆 ТОП СОТРУДНИКОВ ЗА ПОСЛЕДНИЕ 24 ЧАСА:")
    print("-" * 45)
    
    # Импортируем функцию из database.py
    sys.path.append('.')
    
    # Подключаем тестовую конфигурацию
    import test_config
    
    try:
        # Временно патчим sys.modules чтобы избежать проверок config.py
        import sys
        sys.modules['config'] = test_config
        
        import database
        
        # Получаем период за последние 24 часа
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        leaderboard = database.get_staff_leaderboard(start_time, end_time)
        
        if leaderboard:
            for i, staff in enumerate(leaderboard, 1):
                print(f"{i}. {staff['full_name']} ({staff['position']})")
                print(f"   Привлек: {staff['attracted_users']} гостей")
                print(f"   Выдано купонов: {staff['issued_coupons']}")
                print(f"   Погашено купонов: {staff['redeemed_coupons']}")
                print(f"   QR-код: {staff['unique_code']}")
                print()
        else:
            print("❌ Нет данных о сотрудниках")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования функции топа: {e}")
    
    conn.close()
    print("🎉 Тест завершен!")

if __name__ == "__main__":
    test_new_staff_system()
