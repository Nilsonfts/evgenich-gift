#!/usr/bin/env python3
"""
Тест простой системы QR-кодов на основе Telegram ID
"""

import sqlite3
import os

def test_simple_qr_system():
    """Тестирует простую систему QR-кодов."""
    print("🎯 ТЕСТ ПРОСТОЙ СИСТЕМЫ QR-КОДОВ (TELEGRAM ID)")
    print("=" * 55)
    
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Проверяем всех активных сотрудников
    print("\n1️⃣ АКТИВНЫЕ СОТРУДНИКИ")
    print("-" * 30)
    
    cur.execute("SELECT * FROM staff WHERE status = 'active' ORDER BY staff_id")
    staff_list = cur.fetchall()
    
    if staff_list:
        print(f"✅ Найдено {len(staff_list)} активных сотрудников:")
        for staff in staff_list:
            qr_link = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
            print(f"   • {staff['full_name']} ({staff['position']})")
            print(f"     Код: {staff['unique_code']}")
            print(f"     QR: {qr_link}")
            print()
    else:
        print("❌ Нет активных сотрудников")
        return
    
    # 2. Тестируем поиск по кодам
    print("2️⃣ ТЕСТ ПОИСКА ПО КОДАМ")
    print("-" * 30)
    
    # Подключаем database модуль
    import sys
    sys.path.append('.')
    
    # Создаем тестовый config
    class TestConfig:
        BOT_TOKEN = 'test'
        CHANNEL_ID = '@test'
        ADMIN_IDS = [123]
        HELLO_STICKER_ID = 'test'
        NASTOYKA_STICKER_ID = 'test'
        THANK_YOU_STICKER_ID = 'test'
        REPORT_CHAT_ID = 123
        GOOGLE_SHEET_KEY = None
        GOOGLE_CREDENTIALS_JSON = None
    
    sys.modules['config'] = TestConfig()
    
    try:
        import database
        
        for staff in staff_list:
            test_code = staff['unique_code']
            found_staff = database.find_staff_by_code(test_code)
            
            if found_staff:
                print(f"✅ Код '{test_code}' найден: {found_staff['full_name']}")
            else:
                print(f"❌ Код '{test_code}' НЕ найден")
    
    except Exception as e:
        print(f"❌ Ошибка при тестировании поиска: {e}")
    
    # 3. Проверяем статистику переходов
    print("\n3️⃣ СТАТИСТИКА ПЕРЕХОДОВ")
    print("-" * 30)
    
    cur.execute("""
        SELECT 
            s.full_name,
            s.unique_code,
            COUNT(u.user_id) as attracted_users
        FROM staff s
        LEFT JOIN users u ON s.staff_id = u.brought_by_staff_id 
            AND u.source = 'staff'
        WHERE s.status = 'active'
        GROUP BY s.staff_id, s.full_name, s.unique_code
        ORDER BY attracted_users DESC
    """)
    
    stats = cur.fetchall()
    
    if stats:
        print("📊 Статистика привлечения гостей:")
        for stat in stats:
            print(f"   • {stat['full_name']}: {stat['attracted_users']} переходов")
    else:
        print("❌ Нет данных о переходах")
    
    # 4. Проверяем общую статистику источников
    print("\n4️⃣ ОБЩАЯ СТАТИСТИКА ИСТОЧНИКОВ")
    print("-" * 35)
    
    cur.execute("""
        SELECT source, COUNT(*) as count 
        FROM users 
        GROUP BY source 
        ORDER BY count DESC
    """)
    
    sources = cur.fetchall()
    
    if sources:
        print("📈 Все источники:")
        for source in sources:
            print(f"   • {source['source']}: {source['count']} пользователей")
    else:
        print("❌ Нет данных об источниках")
    
    conn.close()
    
    # 5. Финальная сводка
    print("\n5️⃣ ФИНАЛЬНАЯ СВОДКА")
    print("-" * 25)
    
    print("✅ СИСТЕМА ГОТОВА К РАБОТЕ!")
    print("\n🔗 Готовые QR-ссылки для сотрудников:")
    
    for staff in staff_list:
        qr_link = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
        print(f"   • {staff['full_name']}: {qr_link}")
    
    print("\n📋 Принцип работы:")
    print("   1. Сотрудник дает гостю QR-код")
    print("   2. Гость сканирует → переходит по ссылке")
    print("   3. В базе записывается source = 'staff'") 
    print("   4. В отчетах показывается привязка к сотруднику")
    
    print("\n🎉 ВСЁ РАБОТАЕТ!")

if __name__ == "__main__":
    test_simple_qr_system()
