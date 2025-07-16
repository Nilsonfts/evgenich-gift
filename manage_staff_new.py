#!/usr/bin/env python3
"""
Универсальный скрипт управления сотрудниками
"""

import sqlite3
import os

def add_staff_member():
    """Интерактивное добавление сотрудника."""
    print("👥 ДОБАВЛЕНИЕ НОВОГО СОТРУДНИКА")
    print("=" * 40)
    
    # Проверяем базу данных
    db_path = "data/evgenich_data.db"
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    # Получаем данные от пользователя
    print("\n📝 Введите данные сотрудника:")
    
    telegram_id = input("Telegram ID (например, 208281210): ").strip()
    if not telegram_id.isdigit():
        print("❌ Telegram ID должен содержать только цифры!")
        return
    
    full_name = input("Полное имя (например, Кристина Нестерова): ").strip()
    if not full_name:
        print("❌ Полное имя не может быть пустым!")
        return
    
    # Автоматически генерируем короткое имя (первое слово + первая буква второго)
    name_parts = full_name.split()
    if len(name_parts) >= 2:
        short_name = f"{name_parts[0]} {name_parts[1][0]}."
    else:
        short_name = name_parts[0]
    
    position = input("Должность (например, Менеджер): ").strip()
    if not position:
        position = "Сотрудник"
    
    # Спрашиваем какой код использовать
    print(f"\n🔗 Выберите тип QR-кода:")
    print(f"1. Простой (Telegram ID): {telegram_id}")
    print(f"2. Пользовательский код")
    
    choice = input("Выбор (1 или 2): ").strip()
    
    if choice == "2":
        unique_code = input("Введите пользовательский код: ").strip()
        if not unique_code:
            print("❌ Код не может быть пустым!")
            return
    else:
        unique_code = telegram_id
    
    # Добавляем в базу данных
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Проверяем, есть ли уже такой сотрудник
        cur.execute("SELECT staff_id FROM staff WHERE telegram_id = ? OR unique_code = ?", 
                   (int(telegram_id), unique_code))
        existing = cur.fetchone()
        
        if existing:
            print(f"\n⚠️  Сотрудник с таким ID или кодом уже существует!")
            update = input("Обновить данные? (y/n): ").strip().lower()
            
            if update == 'y':
                cur.execute("""
                    UPDATE staff 
                    SET full_name = ?, short_name = ?, position = ?, unique_code = ?, status = 'active'
                    WHERE telegram_id = ?
                """, (full_name, short_name, position, unique_code, int(telegram_id)))
                action = "обновлен"
            else:
                print("❌ Операция отменена")
                conn.close()
                return
        else:
            cur.execute("""
                INSERT INTO staff (telegram_id, full_name, short_name, position, unique_code, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (int(telegram_id), full_name, short_name, position, unique_code))
            action = "добавлен"
        
        conn.commit()
        conn.close()
        
        # Выводим результат
        qr_link = f"https://t.me/evgenichspbbot?start=w_{unique_code}"
        
        print(f"\n🎉 Сотрудник успешно {action}!")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Полное имя: {full_name}")
        print(f"   Короткое имя: {short_name}")
        print(f"   Должность: {position}")
        print(f"   QR-код: {unique_code}")
        print(f"   QR-ссылка: {qr_link}")
        
        print(f"\n✅ Готово! Сотрудник может использовать QR-ссылку для привлечения гостей.")
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении сотрудника: {e}")

def list_all_staff():
    """Показывает всех сотрудников."""
    print("👥 СПИСОК ВСЕХ СОТРУДНИКОВ")
    print("=" * 35)
    
    db_path = "data/evgenich_data.db"
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM staff ORDER BY status DESC, staff_id")
        staff_list = cur.fetchall()
        
        if staff_list:
            for staff in staff_list:
                status_icon = "✅" if staff['status'] == 'active' else "❌"
                qr_link = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
                
                print(f"\n{status_icon} {staff['full_name']} ({staff['position']})")
                print(f"   ID: {staff['staff_id']} | TG: {staff['telegram_id']}")
                print(f"   Код: {staff['unique_code']}")
                print(f"   QR: {qr_link}")
        else:
            print("❌ Сотрудников не найдено")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🎯 УПРАВЛЕНИЕ СОТРУДНИКАМИ")
    print("=" * 30)
    print("1. Добавить сотрудника")
    print("2. Показать всех сотрудников")
    
    choice = input("\nВыберите действие (1 или 2): ").strip()
    
    if choice == "1":
        add_staff_member()
    elif choice == "2":
        list_all_staff()
    else:
        print("❌ Неверный выбор!")
