#!/usr/bin/env python3
"""
Добавляем Кристину с простым кодом по Telegram ID
"""

import sqlite3
import os

def add_kristina_staff():
    """Добавляет Кристину как сотрудника с кодом по Telegram ID."""
    
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    print("👥 Добавляем Кристину как сотрудника...")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Данные Кристины
    telegram_id = 208281210
    full_name = "Кристина Нестерова"
    short_name = "Кристина"
    unique_code = str(telegram_id)  # Используем Telegram ID как код
    position = "Менеджер"
    
    try:
        # Проверяем, есть ли уже такой сотрудник
        cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        
        if existing:
            print(f"✅ Кристина уже есть в базе! Код: {existing[4]}")
        else:
            # Добавляем нового сотрудника
            cur.execute("""
                INSERT INTO staff (telegram_id, full_name, short_name, unique_code, position, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (telegram_id, full_name, short_name, unique_code, position))
            
            conn.commit()
            print(f"✅ Кристина добавлена! Код: {unique_code}")
        
        # Показываем QR-ссылку
        qr_url = f"https://t.me/evgenichspbbot?start=w_{unique_code}"
        print(f"🔗 QR-ссылка: {qr_url}")
        
        # Проверяем всех сотрудников
        print(f"\n👥 Все активные сотрудники:")
        cur.execute("SELECT telegram_id, full_name, unique_code FROM staff WHERE status = 'active'")
        staff_list = cur.fetchall()
        
        for staff in staff_list:
            print(f"• {staff[1]} (ID: {staff[0]}, код: {staff[2]})")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    add_kristina_staff()
