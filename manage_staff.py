#!/usr/bin/env python3
"""
Инструмент для управления сотрудниками в базе данных
"""

import sqlite3
import sys

def clean_test_staff():
    """Удаляет тестовых сотрудников без telegram_id"""
    print("🧹 ОЧИСТКА ТЕСТОВЫХ СОТРУДНИКОВ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cur = conn.cursor()
        
        # Показываем, кого будем удалять
        cur.execute("SELECT staff_id, full_name, unique_code FROM staff WHERE telegram_id IS NULL")
        test_staff = cur.fetchall()
        
        if not test_staff:
            print("✅ Тестовых сотрудников не найдено")
            return
        
        print("📋 Будут удалены следующие тестовые сотрудники:")
        for staff_id, full_name, unique_code in test_staff:
            print(f"  • {full_name} (код: {unique_code})")
        
        # Подтверждение
        confirm = input("\n⚠️ Вы уверены? Это действие нельзя отменить! (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Операция отменена")
            return
        
        # Удаляем тестовых сотрудников
        cur.execute("DELETE FROM staff WHERE telegram_id IS NULL")
        deleted_count = cur.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ Удалено {deleted_count} тестовых сотрудников")
        print("💡 Теперь реальные сотрудники могут зарегистрироваться через /staff_reg")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def add_telegram_id_to_staff():
    """Добавляет telegram_id существующему сотруднику"""
    print("🔧 ДОБАВЛЕНИЕ TELEGRAM_ID СОТРУДНИКУ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cur = conn.cursor()
        
        # Показываем сотрудников без telegram_id
        cur.execute("SELECT staff_id, full_name, unique_code FROM staff WHERE telegram_id IS NULL")
        staff_without_tg = cur.fetchall()
        
        if not staff_without_tg:
            print("✅ Все сотрудники уже имеют telegram_id")
            return
        
        print("📋 Сотрудники без telegram_id:")
        for i, (staff_id, full_name, unique_code) in enumerate(staff_without_tg, 1):
            print(f"  {i}. {full_name} (код: {unique_code}, ID: {staff_id})")
        
        # Выбор сотрудника
        try:
            choice = int(input("\nВыберите номер сотрудника: ")) - 1
            if choice < 0 or choice >= len(staff_without_tg):
                print("❌ Неверный выбор")
                return
        except ValueError:
            print("❌ Введите число")
            return
        
        staff_id, full_name, unique_code = staff_without_tg[choice]
        
        # Ввод telegram_id
        try:
            telegram_id = int(input(f"Введите Telegram ID для {full_name}: "))
        except ValueError:
            print("❌ Telegram ID должен быть числом")
            return
        
        # Проверяем, что этот telegram_id не занят
        cur.execute("SELECT full_name FROM staff WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        if existing:
            print(f"❌ Telegram ID {telegram_id} уже используется сотрудником {existing[0]}")
            return
        
        # Обновляем telegram_id
        cur.execute("UPDATE staff SET telegram_id = ? WHERE staff_id = ?", (telegram_id, staff_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Сотруднику {full_name} добавлен Telegram ID: {telegram_id}")
        print(f"💡 Теперь QR-код с кодом '{unique_code}' будет работать для этого сотрудника")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def show_staff_status():
    """Показывает текущий статус всех сотрудников"""
    print("📊 СТАТУС СОТРУДНИКОВ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM staff ORDER BY staff_id")
        all_staff = cur.fetchall()
        
        if not all_staff:
            print("❌ Сотрудников не найдено")
            return
        
        print("👥 Все сотрудники:")
        for staff in all_staff:
            staff_id, full_name, short_name, unique_code, position, status, telegram_id, created_at = staff
            
            if telegram_id:
                status_icon = "✅"
                status_text = f"Реальный (TG: {telegram_id})"
            else:
                status_icon = "⚠️"
                status_text = "Тестовый (без TG ID)"
            
            print(f"  {status_icon} {full_name}")
            print(f"    Код: {unique_code}")
            print(f"    Должность: {position}")
            print(f"    Статус: {status_text}")
            print()
        
        # Статистика
        cur.execute("SELECT COUNT(*) FROM staff WHERE telegram_id IS NOT NULL")
        real_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM staff WHERE telegram_id IS NULL")
        test_count = cur.fetchone()[0]
        
        print(f"📈 Статистика:")
        print(f"  • Реальных сотрудников: {real_count}")
        print(f"  • Тестовых сотрудников: {test_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    """Главное меню"""
    while True:
        print("\n" + "="*50)
        print("🛠️ УПРАВЛЕНИЕ СОТРУДНИКАМИ")
        print("="*50)
        print("1. Показать статус сотрудников")
        print("2. Добавить Telegram ID сотруднику")
        print("3. Удалить тестовых сотрудников")
        print("0. Выход")
        
        choice = input("\nВыберите действие: ")
        
        if choice == "1":
            show_staff_status()
        elif choice == "2":
            add_telegram_id_to_staff()
        elif choice == "3":
            clean_test_staff()
        elif choice == "0":
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()
