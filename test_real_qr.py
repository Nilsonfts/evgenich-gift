#!/usr/bin/env python3
"""
Тест реального QR-кода сотрудника
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3

def test_real_qr_code():
    """Тестирует обработку реального QR-кода"""
    print("🧪 ТЕСТ РЕАЛЬНОГО QR-КОДА СОТРУДНИКА")
    print("=" * 50)
    
    try:
        # Подключаемся к реальной базе данных
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Получаем список активных кодов
        cur.execute("SELECT unique_code, full_name, short_name FROM staff WHERE status = 'active'")
        active_staff = cur.fetchall()
        
        print("📋 Активные сотрудники:")
        for staff in active_staff:
            print(f"  • {staff['full_name']} → код: {staff['unique_code']}")
        
        if not active_staff:
            print("❌ Нет активных сотрудников!")
            return
        
        # Берем первый код для теста
        test_code = active_staff[0]['unique_code']
        test_name = active_staff[0]['full_name']
        
        print(f"\n🎯 Тестируем код: {test_code} (сотрудник: {test_name})")
        
        # Имитируем логику из handle_start
        payload = f"w_{test_code}"
        print(f"📱 QR-ссылка: https://t.me/bot?start={payload}")
        
        # Извлекаем код из payload
        if payload.startswith('w_'):
            staff_code = payload.replace('w_', '')
            print(f"🔍 Извлеченный код: {staff_code}")
            
            # Ищем сотрудника
            cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (staff_code,))
            staff_member = cur.fetchone()
            
            if staff_member:
                print(f"✅ Сотрудник найден:")
                print(f"   ID: {staff_member['staff_id']}")
                print(f"   Имя: {staff_member['full_name']}")
                print(f"   Краткое имя: {staff_member['short_name']}")
                print(f"   Код: {staff_member['unique_code']}")
                print(f"   Статус: {staff_member['status']}")
                print(f"   Telegram ID: {staff_member['telegram_id']}")
                
                # Проверяем, что произойдет при регистрации пользователя
                test_user_id = 999999
                source = f"Сотрудник: {staff_member['short_name']}"
                brought_by_staff_id = staff_member['staff_id']
                
                print(f"\n📝 Результат регистрации пользователя:")
                print(f"   User ID: {test_user_id}")
                print(f"   Source: {source}")
                print(f"   Brought by staff ID: {brought_by_staff_id}")
                
                print(f"\n🎉 QR-код работает корректно!")
                
            else:
                print(f"❌ Сотрудник НЕ найден для кода: {staff_code}")
                print("🔍 Возможные причины:")
                print("   • Код неправильный")
                print("   • Сотрудник неактивен")
                print("   • Ошибка в базе данных")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

def test_with_user_codes():
    """Тестирует с кодами, которые пользователь может использовать"""
    print("\n🔧 ТЕСТ С ПОЛЬЗОВАТЕЛЬСКИМИ КОДАМИ")
    print("=" * 50)
    
    # Коды, которые могут использовать пользователи
    test_codes = ['IVAN2024', 'MARIA2024', 'ALEX2024', 'ELENA2024', 'ТЕСТ2024']
    
    try:
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        for code in test_codes:
            print(f"\n🧪 Тестируем код: {code}")
            
            cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (code,))
            staff_member = cur.fetchone()
            
            if staff_member:
                print(f"  ✅ Найден: {staff_member['full_name']}")
                print(f"     Source будет: Сотрудник: {staff_member['short_name']}")
                print(f"     Staff ID: {staff_member['staff_id']}")
            else:
                print(f"  ❌ НЕ найден!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_real_qr_code()
    test_with_user_codes()
