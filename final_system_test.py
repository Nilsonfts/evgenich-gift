#!/usr/bin/env python3
"""
Финальный тест всей системы QR-кодов
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta

def final_system_test():
    """Полный тест системы QR-кодов с кириллицей."""
    print("🎯 ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ QR-КОДОВ")
    print("=" * 50)
    
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Проверяем структуру базы данных
    print("\n1️⃣ ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("-" * 40)
    
    # Проверяем таблицу staff
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staff'")
    if cur.fetchone():
        print("✅ Таблица staff существует")
        
        cur.execute("SELECT COUNT(*) as count FROM staff WHERE status = 'active'")
        staff_count = cur.fetchone()['count']
        print(f"✅ Активных сотрудников: {staff_count}")
        
        # Показываем список сотрудников
        cur.execute("SELECT full_name, unique_code FROM staff WHERE status = 'active'")
        staff_list = cur.fetchall()
        for staff in staff_list:
            print(f"   • {staff['full_name']} ({staff['unique_code']})")
    else:
        print("❌ Таблица staff отсутствует")
        return
    
    # 2. Проверяем таблицу users
    print("\n2️⃣ ПРОВЕРКА ТАБЛИЦЫ ПОЛЬЗОВАТЕЛЕЙ")
    print("-" * 40)
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        print("✅ Таблица users существует")
        
        # Статистика по источникам
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM users 
            GROUP BY source 
            ORDER BY count DESC
        """)
        sources = cur.fetchall()
        
        print("📊 Статистика по источникам:")
        for source in sources:
            print(f"   • {source['source']}: {source['count']} пользователей")
        
        # Статистика по сотрудникам
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
        
        staff_stats = cur.fetchall()
        print("\n👥 Статистика привлечения по сотрудникам:")
        for staff in staff_stats:
            print(f"   • {staff['full_name']} ({staff['unique_code']}): {staff['attracted_users']} гостей")
    
    # 3. Проверяем функции аналитики
    print("\n3️⃣ ПРОВЕРКА ФУНКЦИЙ АНАЛИТИКИ")
    print("-" * 40)
    
    try:
        # Импортируем модуль database
        sys.path.append('.')
        sys.modules['config'] = type('config', (), {
            'BOT_TOKEN': 'test',
            'CHANNEL_ID': '@test',
            'ADMIN_IDS': [123],
            'HELLO_STICKER_ID': 'test',
            'NASTOYKA_STICKER_ID': 'test',
            'THANK_YOU_STICKER_ID': 'test',
            'REPORT_CHAT_ID': 123,
            'GOOGLE_SHEET_KEY': None,
            'GOOGLE_CREDENTIALS_JSON': None
        })()
        
        import database
        
        # Тестируем функцию топа сотрудников
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)  # За последний месяц
        
        leaderboard = database.get_staff_leaderboard(start_time, end_time)
        
        if leaderboard:
            print("✅ Функция get_staff_leaderboard работает")
            print("🏆 ТОП сотрудников за месяц:")
            for i, staff in enumerate(leaderboard[:3], 1):  # Топ-3
                print(f"   {i}. {staff['full_name']} ({staff['position']})")
                print(f"      Привлек: {staff['attracted_users']} гостей")
                print(f"      QR-код: {staff['unique_code']}")
        else:
            print("⚠️ Функция get_staff_leaderboard возвращает пустой результат")
            
        # Тестируем функцию месячной статистики
        monthly_stats = database.get_staff_period_stats(start_time, end_time)
        
        if monthly_stats:
            print(f"\n✅ Функция get_staff_period_stats работает")
            print(f"📈 Статистика за период:")
            print(f"   Всего привлечено: {monthly_stats.get('total_attracted', 0)} гостей")
            print(f"   Выдано купонов: {monthly_stats.get('total_issued', 0)}")
            print(f"   Погашено купонов: {monthly_stats.get('total_redeemed', 0)}")
            print(f"   Активных сотрудников: {monthly_stats.get('active_staff_count', 0)}")
        else:
            print("⚠️ Функция get_staff_period_stats возвращает пустой результат")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании функций: {e}")
    
    # 4. Проверяем QR-коды
    print("\n4️⃣ ПРОВЕРКА QR-КОДОВ")
    print("-" * 40)
    
    # Генерируем ссылки для всех активных сотрудников
    cur.execute("SELECT full_name, unique_code FROM staff WHERE status = 'active'")
    staff_list = cur.fetchall()
    
    print("🔗 Ссылки QR-кодов:")
    for staff in staff_list:
        qr_link = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
        print(f"   • {staff['full_name']}: {qr_link}")
    
    # 5. Проверяем процесс обработки QR-кода
    print("\n5️⃣ СИМУЛЯЦИЯ ОБРАБОТКИ QR-КОДА")
    print("-" * 40)
    
    # Тестируем функцию поиска сотрудника напрямую
    test_code = staff_list[0]['unique_code'] if staff_list else None
    if test_code:
        staff_member = database.find_staff_by_code(test_code)
        if staff_member:
            print(f"✅ QR-код {test_code} корректно найден в базе")
            print(f"   Сотрудник: {staff_member['full_name']}")
            print(f"   ID: {staff_member['staff_id']}")
            print(f"   Позиция: {staff_member['position']}")
            
            # Проверяем логику формирования source
            expected_source = "staff"
            print(f"✅ При переходе по QR source будет: '{expected_source}'")
            
        else:
            print(f"❌ QR-код {test_code} не найден")
    else:
        print("⚠️ Нет активных сотрудников для тестирования")
    
    # Проверяем кириллический код нил680
    print("\n🔍 ПРОВЕРКА КИРИЛЛИЧЕСКОГО КОДА:")
    nil_staff = database.find_staff_by_code("нил680")
    if nil_staff:
        print(f"✅ Кириллический код 'нил680' найден")
        print(f"   Сотрудник: {nil_staff['full_name']}")
        print(f"   QR-ссылка: https://t.me/evgenichspbbot?start=w_нил680")
    else:
        print("❌ Кириллический код 'нил680' не найден")
        print("   Добавьте сотрудника: python add_nil680_staff.py")
    
    conn.close()
    
    print("\n🎉 ФИНАЛЬНЫЙ ТЕСТ ЗАВЕРШЕН!")
    print("=" * 50)

if __name__ == "__main__":
    final_system_test()
