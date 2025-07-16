#!/usr/bin/env python3
"""
Простое управление сотрудниками - используем Telegram ID как уникальный код
"""

import sqlite3
import os

def add_staff_member(telegram_id, full_name, short_name, position):
    """Добавляет или обновляет сотрудника с Telegram ID как кодом."""
    
    if not os.path.exists("data/evgenich_data.db"):
        print("❌ База данных не найдена!")
        return False
    
    conn = sqlite3.connect("data/evgenich_data.db")
    cur = conn.cursor()
    
    try:
        # Проверяем, существует ли уже такой сотрудник
        cur.execute("SELECT * FROM staff WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        
        if existing:
            # Обновляем существующего
            cur.execute("""
                UPDATE staff 
                SET full_name = ?, short_name = ?, position = ?, unique_code = ?, status = 'active'
                WHERE telegram_id = ?
            """, (full_name, short_name, position, str(telegram_id), telegram_id))
            print(f"✅ Сотрудник {full_name} обновлен")
        else:
            # Добавляем нового
            cur.execute("""
                INSERT INTO staff (telegram_id, full_name, short_name, position, unique_code, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (telegram_id, full_name, short_name, position, str(telegram_id)))
            print(f"✅ Сотрудник {full_name} добавлен")
        
        conn.commit()
        
        # Показываем QR-ссылку
        qr_link = f"https://t.me/evgenichspbbot?start=w_{telegram_id}"
        print(f"🔗 QR-ссылка: {qr_link}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        conn.close()

def list_staff_members():
    """Показывает всех активных сотрудников."""
    
    if not os.path.exists("data/evgenich_data.db"):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect("data/evgenich_data.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM staff WHERE status = 'active' ORDER BY full_name")
        staff_list = cur.fetchall()
        
        if not staff_list:
            print("❌ Нет активных сотрудников")
            return
        
        print("\n👥 АКТИВНЫЕ СОТРУДНИКИ:")
        print("=" * 60)
        
        for staff in staff_list:
            print(f"• {staff['full_name']} ({staff['position']})")
            print(f"  ID: {staff['telegram_id']}")
            print(f"  Код: {staff['unique_code']}")
            print(f"  QR: https://t.me/evgenichspbbot?start=w_{staff['unique_code']}")
            print()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

def test_qr_code(telegram_id):
    """Тестирует QR-код сотрудника."""
    
    if not os.path.exists("data/evgenich_data.db"):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect("data/evgenich_data.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Ищем сотрудника по коду (который равен telegram_id)
        cur.execute("SELECT * FROM staff WHERE unique_code = ? AND status = 'active'", (str(telegram_id),))
        staff = cur.fetchone()
        
        if staff:
            print(f"✅ QR-код {telegram_id} найден!")
            print(f"   Сотрудник: {staff['full_name']}")
            print(f"   Позиция: {staff['position']}")
            print(f"   QR-ссылка: https://t.me/evgenichspbbot?start=w_{telegram_id}")
            print(f"   ✅ При переходе source будет: 'staff'")
        else:
            print(f"❌ QR-код {telegram_id} не найден в базе")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

def main():
    """Главное меню управления сотрудниками."""
    
    print("🏢 УПРАВЛЕНИЕ СОТРУДНИКАМИ")
    print("=" * 30)
    print("1. Добавить сотрудника")
    print("2. Показать всех сотрудников") 
    print("3. Тестировать QR-код")
    print("4. Добавить Кристину (208281210)")
    print("5. Выход")
    
    while True:
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == "1":
            print("\n📝 ДОБАВЛЕНИЕ СОТРУДНИКА")
            telegram_id = input("Telegram ID: ").strip()
            full_name = input("Полное имя: ").strip()
            short_name = input("Короткое имя: ").strip()
            position = input("Должность: ").strip()
            
            if telegram_id and full_name and short_name and position:
                try:
                    telegram_id = int(telegram_id)
                    add_staff_member(telegram_id, full_name, short_name, position)
                except ValueError:
                    print("❌ Telegram ID должен быть числом")
            else:
                print("❌ Все поля обязательны")
                
        elif choice == "2":
            list_staff_members()
            
        elif choice == "3":
            telegram_id = input("Введите Telegram ID для тестирования: ").strip()
            if telegram_id:
                try:
                    telegram_id = int(telegram_id)
                    test_qr_code(telegram_id)
                except ValueError:
                    print("❌ Telegram ID должен быть числом")
                    
        elif choice == "4":
            print("\n👩 ДОБАВЛЕНИЕ КРИСТИНЫ")
            add_staff_member(208281210, "Кристина", "Кристина", "Менеджер")
            
        elif choice == "5":
            print("👋 До свидания!")
            break
            
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()
