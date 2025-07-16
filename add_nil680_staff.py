#!/usr/bin/env python3
"""
Добавление реального сотрудника с кодом нил680
"""

import sqlite3
import os

def add_real_staff():
    """Добавляет реального сотрудника с кодом нил680."""
    
    # Используем правильную базу данных
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена! Сначала запустите init_correct_db.py")
        return
    
    # Данные реального сотрудника
    staff_data = {
        'telegram_id': 196614680,  # Ваш Telegram ID из логов
        'full_name': 'Нил Владимирович',  # Предполагаемое полное имя
        'short_name': 'Нил В.',
        'unique_code': 'нил680',  # Точно как в QR-коде
        'position': 'Администратор'
    }
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Проверяем, есть ли уже сотрудник с таким telegram_id
        cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (staff_data['telegram_id'],))
        existing = cur.fetchone()
        
        if existing:
            print(f"⚠️ Обновляю существующего сотрудника...")
            cur.execute("""
                UPDATE staff 
                SET full_name = ?, short_name = ?, unique_code = ?, position = ?, status = 'active'
                WHERE telegram_id = ?
            """, (
                staff_data['full_name'],
                staff_data['short_name'], 
                staff_data['unique_code'],
                staff_data['position'],
                staff_data['telegram_id']
            ))
        else:
            print(f"✅ Добавляю нового сотрудника...")
            cur.execute("""
                INSERT INTO staff (telegram_id, full_name, short_name, unique_code, position, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (
                staff_data['telegram_id'],
                staff_data['full_name'],
                staff_data['short_name'],
                staff_data['unique_code'],
                staff_data['position']
            ))
        
        conn.commit()
        
        print(f"🎉 Сотрудник успешно добавлен/обновлен:")
        print(f"   Telegram ID: {staff_data['telegram_id']}")
        print(f"   Полное имя: {staff_data['full_name']}")
        print(f"   Код: {staff_data['unique_code']}")
        print(f"   QR-ссылка: https://t.me/evgenichspbbot?start=w_{staff_data['unique_code']}")
        print(f"")
        print(f"✅ Теперь ваша ссылка будет работать правильно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    conn.close()

def test_qr_code():
    """Тестирует QR-код с кириллическим кодом."""
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    print(f"\\n🧪 ТЕСТ QR-КОДА С КИРИЛЛИЦЕЙ")
    print("=" * 40)
    
    # Симулируем переход по вашей ссылке
    payload = "w_нил680"
    
    if payload.startswith('w_'):
        staff_code = payload.replace('w_', '')
        print(f"📝 Извлеченный код: '{staff_code}'")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Ищем сотрудника (как в user_commands.py)
        cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (staff_code,))
        staff_member = cur.fetchone()
        
        if staff_member:
            brought_by_staff_id = staff_member['staff_id']
            source = f"Сотрудник: {staff_member['short_name']}"
            
            print(f"✅ СОТРУДНИК НАЙДЕН!")
            print(f"   Имя: {staff_member['full_name']}")
            print(f"   ID: {staff_member['staff_id']}")
            print(f"   📊 Источник будет: {source}")
            print(f"   🔗 brought_by_staff_id: {brought_by_staff_id}")
        else:
            print(f"❌ СОТРУДНИК НЕ НАЙДЕН!")
            print(f"   📊 Источник будет: direct")
        
        conn.close()

if __name__ == "__main__":
    print("🔧 ДОБАВЛЕНИЕ СОТРУДНИКА С КОДОМ 'нил680'")
    print("=" * 50)
    
    add_real_staff()
    test_qr_code()
