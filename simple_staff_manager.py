#!/usr/bin/env python3
"""
Простая система регистрации сотрудников с кодами по Telegram ID
"""

import sqlite3
import os

def add_staff_by_telegram_id(telegram_id, full_name, short_name, position):
    """
    Добавляет сотрудника с кодом равным его Telegram ID.
    
    Args:
        telegram_id (int): Telegram ID сотрудника
        full_name (str): Полное имя
        short_name (str): Короткое имя
        position (str): Должность
    """
    
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Проверяем, есть ли уже такой сотрудник
        cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        
        if existing:
            print(f"✅ Сотрудник с ID {telegram_id} уже существует!")
            return False
        
        # Добавляем нового сотрудника (код = Telegram ID)
        unique_code = str(telegram_id)
        
        cur.execute("""
            INSERT INTO staff (telegram_id, full_name, short_name, unique_code, position, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (telegram_id, full_name, short_name, unique_code, position))
        
        conn.commit()
        
        # Генерируем QR-ссылку
        qr_url = f"https://t.me/evgenichspbbot?start=w_{unique_code}"
        
        print(f"✅ Сотрудник добавлен!")
        print(f"👤 Имя: {full_name}")
        print(f"📍 Должность: {position}")
        print(f"🔢 Код: {unique_code}")
        print(f"🔗 QR-ссылка: {qr_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    finally:
        conn.close()

def list_all_staff():
    """Показывает всех активных сотрудников с их QR-кодами."""
    
    db_path = "data/evgenich_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT telegram_id, full_name, short_name, unique_code, position 
            FROM staff 
            WHERE status = 'active'
            ORDER BY full_name
        """)
        
        staff_list = cur.fetchall()
        
        print(f"\n👥 АКТИВНЫЕ СОТРУДНИКИ ({len(staff_list)}):")
        print("=" * 50)
        
        for staff in staff_list:
            qr_url = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
            print(f"👤 {staff['full_name']} ({staff['position']})")
            print(f"   ID: {staff['telegram_id']}")
            print(f"   Код: {staff['unique_code']}")
            print(f"   QR: {qr_url}")
            print()
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        conn.close()

def main():
    """Главная функция для управления сотрудниками."""
    
    print("🏢 СИСТЕМА УПРАВЛЕНИЯ СОТРУДНИКАМИ")
    print("=" * 40)
    
    while True:
        print("\nВыберите действие:")
        print("1. Добавить сотрудника")
        print("2. Показать всех сотрудников")
        print("3. Выход")
        
        choice = input("\nВаш выбор: ").strip()
        
        if choice == '1':
            print("\n📝 Добавление нового сотрудника:")
            try:
                telegram_id = int(input("Telegram ID: "))
                full_name = input("Полное имя: ").strip()
                short_name = input("Короткое имя: ").strip()
                position = input("Должность: ").strip()
                
                if all([telegram_id, full_name, short_name, position]):
                    add_staff_by_telegram_id(telegram_id, full_name, short_name, position)
                else:
                    print("❌ Все поля обязательны!")
                    
            except ValueError:
                print("❌ Telegram ID должен быть числом!")
        
        elif choice == '2':
            list_all_staff()
        
        elif choice == '3':
            print("👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор!")

if __name__ == "__main__":
    # Быстрое добавление известных сотрудников
    known_staff = [
        (208281210, "Кристина Нестерова", "Кристина", "Менеджер"),
        # Добавьте других сотрудников здесь
    ]
    
    print("🚀 Инициализация известных сотрудников...")
    for telegram_id, full_name, short_name, position in known_staff:
        add_staff_by_telegram_id(telegram_id, full_name, short_name, position)
    
    # Показываем всех сотрудников
    list_all_staff()
    
    # Интерактивное меню (опционально)
    # main()
