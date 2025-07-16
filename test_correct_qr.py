#!/usr/bin/env python3
"""
Тест QR-системы с правильной базой данных
"""

import sqlite3
import os

def test_qr_with_correct_db():
    """Тестирует QR-систему с правильной базой данных."""
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ Правильная база данных не найдена! Запустите init_correct_db.py")
        return
    
    print("🧪 ТЕСТ QR-СИСТЕМЫ С ПРАВИЛЬНОЙ БАЗОЙ ДАННЫХ")
    print("=" * 55)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Проверяем существующих сотрудников
    cur.execute("SELECT * FROM staff WHERE status = 'active'")
    staff_members = cur.fetchall()
    
    print(f"👥 Активных сотрудников: {len(staff_members)}")
    
    for staff in staff_members:
        print(f"\n🔍 Тестирую сотрудника: {staff['full_name']}")
        print(f"   Код: {staff['unique_code']}")
        print(f"   Telegram ID: {staff['telegram_id']}")
        print(f"   QR-ссылка: https://t.me/EvgenichTapBarBot?start=w_{staff['unique_code']}")
        
        # Симулируем переход по QR-коду
        payload = f"w_{staff['unique_code']}"
        
        if payload.startswith('w_'):
            staff_code = payload.replace('w_', '')
            print(f"   📝 Извлеченный код: {staff_code}")
            
            # Ищем сотрудника (как в user_commands.py)
            cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (staff_code,))
            found_staff = cur.fetchone()
            
            if found_staff:
                brought_by_staff_id = found_staff['staff_id']
                source = f"Сотрудник: {found_staff['short_name']}"
                
                print(f"   ✅ СОТРУДНИК НАЙДЕН!")
                print(f"   📊 Источник: {source}")
                print(f"   🔗 brought_by_staff_id: {brought_by_staff_id}")
                
                # Симулируем добавление пользователя
                test_user_id = 777777777
                
                try:
                    cur.execute("""
                        INSERT OR REPLACE INTO users 
                        (user_id, username, first_name, source, brought_by_staff_id, status)
                        VALUES (?, ?, ?, ?, ?, 'registered')
                    """, (test_user_id, "test_user", "Тестовый Пользователь", source, brought_by_staff_id))
                    
                    conn.commit()
                    print(f"   ✅ Тестовый пользователь добавлен!")
                    
                except Exception as e:
                    print(f"   ❌ Ошибка добавления пользователя: {e}")
                    
            else:
                print(f"   ❌ СОТРУДНИК НЕ НАЙДЕН!")
                print(f"   📊 Источник будет: direct")
    
    # Проверяем результаты
    print(f"\n📊 ПРОВЕРКА РЕЗУЛЬТАТОВ:")
    print("-" * 30)
    
    cur.execute("""
        SELECT u.user_id, u.source, u.brought_by_staff_id, s.full_name as staff_name
        FROM users u
        LEFT JOIN staff s ON u.brought_by_staff_id = s.staff_id
        ORDER BY u.rowid DESC
        LIMIT 5
    """)
    
    users = cur.fetchall()
    
    if users:
        for user in users:
            if user['brought_by_staff_id']:
                print(f"✅ Пользователь {user['user_id']}: {user['source']} → привел {user['staff_name']} (ID: {user['brought_by_staff_id']})")
            else:
                print(f"❌ Пользователь {user['user_id']}: {user['source']} → без сотрудника")
    else:
        print("❌ Нет пользователей в базе")
    
    conn.close()

def create_real_staff_example():
    """Создает пример реального сотрудника."""
    db_path = "data/evgenich_data.db"
    
    print(f"\n👤 СОЗДАНИЕ ПРИМЕРА РЕАЛЬНОГО СОТРУДНИКА")
    print("-" * 45)
    
    # Данные как если бы сотрудник реально зарегистрировался
    real_staff = {
        'telegram_id': 196614680,  # ID из ваших логов
        'full_name': 'Евгений Владимирович',
        'short_name': 'Евгений В.',
        'unique_code': 'EVGENIY2024',
        'position': 'Администратор'
    }
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT OR REPLACE INTO staff (telegram_id, full_name, short_name, unique_code, position, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (
            real_staff['telegram_id'],
            real_staff['full_name'],
            real_staff['short_name'],
            real_staff['unique_code'],
            real_staff['position']
        ))
        
        conn.commit()
        
        print(f"✅ Создан реальный сотрудник:")
        print(f"   Telegram ID: {real_staff['telegram_id']}")
        print(f"   Имя: {real_staff['full_name']}")
        print(f"   Код: {real_staff['unique_code']}")
        print(f"   QR-ссылка: https://t.me/EvgenichTapBarBot?start=w_{real_staff['unique_code']}")
        print(f"\n💡 Теперь можете протестировать этот QR-код!")
        
    except Exception as e:
        print(f"❌ Ошибка создания сотрудника: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_qr_with_correct_db()
    create_real_staff_example()
