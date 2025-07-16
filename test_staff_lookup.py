#!/usr/bin/env python3
"""
Тест поиска сотрудников по QR-кодам
"""

import sqlite3

def test_staff_lookup():
    """Тестирует поиск сотрудников по кодам."""
    print("🔍 ТЕСТ ПОИСКА СОТРУДНИКОВ ПО QR-КОДАМ")
    print("=" * 50)
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    cur = conn.cursor()
    
    # Получаем всех активных сотрудников
    cur.execute("SELECT * FROM staff WHERE status = 'active'")
    staff_members = cur.fetchall()
    
    print(f"👥 Активных сотрудников в базе: {len(staff_members)}")
    print()
    
    # Тестируем поиск для каждого сотрудника
    for staff in staff_members:
        code = staff['unique_code']
        print(f"🔍 Тестирую код: '{code}'")
        
        # Имитируем поиск как в database.py
        cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (code,))
        found_staff = cur.fetchone()
        
        if found_staff:
            print(f"   ✅ Найден: {found_staff['full_name']} (ID: {found_staff['staff_id']})")
            print(f"   📋 Короткое имя: {found_staff['short_name']}")
            print(f"   📱 Telegram ID: {found_staff['telegram_id']}")
        else:
            print(f"   ❌ НЕ НАЙДЕН!")
        print()
    
    # Тестируем обработку QR-ссылки
    print("🔗 ТЕСТ ОБРАБОТКИ QR-ССЫЛОК:")
    print("-" * 30)
    
    test_payloads = ["w_IVAN2024", "w_MARIA2024", "w_FAKE123"]
    
    for payload in test_payloads:
        print(f"🔍 Тестирую payload: '{payload}'")
        
        if payload.startswith('w_'):
            staff_code = payload.replace('w_', '')
            print(f"   📝 Извлеченный код: '{staff_code}'")
            
            cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (staff_code,))
            found_staff = cur.fetchone()
            
            if found_staff:
                print(f"   ✅ Сотрудник найден: {found_staff['full_name']}")
                print(f"   📊 Источник будет: 'Сотрудник: {found_staff['short_name']}'")
                print(f"   🔗 brought_by_staff_id: {found_staff['staff_id']}")
            else:
                print(f"   ❌ Сотрудник НЕ найден - источник будет 'direct'")
        print()
    
    conn.close()

if __name__ == "__main__":
    test_staff_lookup()
