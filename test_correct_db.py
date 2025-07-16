#!/usr/bin/env python3
"""
Тест с правильной базой данных evgenich_data.db
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Создаем минимальную заглушку для config, чтобы избежать ошибок
class MockConfig:
    GOOGLE_SHEET_KEY = None
    GOOGLE_CREDENTIALS_JSON = None

sys.modules['config'] = MockConfig()

import sqlite3

def test_correct_database():
    """Тестирует правильную базу данных evgenich_data.db"""
    print("🔍 ТЕСТ ПРАВИЛЬНОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Путь к правильной базе данных
    data_dir = "data"
    db_file = os.path.join(data_dir, "evgenich_data.db")
    
    print(f"📂 Папка data: {os.path.exists(data_dir)}")
    print(f"🗄️ База данных: {db_file}")
    print(f"📁 Файл существует: {os.path.exists(db_file)}")
    
    if not os.path.exists(db_file):
        print("❌ Правильная база данных НЕ существует!")
        print("💡 Это объясняет, почему QR-коды не работают в продакшне")
        print("\n🛠️ РЕШЕНИЕ:")
        print("1. Нужно инициализировать базу данных через database.init_db()")
        print("2. Или скопировать данные из bot_database.db в evgenich_data.db")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Проверяем таблицы
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cur.fetchall()]
        
        print(f"\n📋 Таблицы в базе данных:")
        for table in tables:
            print(f"  • {table}")
        
        if 'staff' in tables:
            cur.execute("SELECT COUNT(*) as count FROM staff")
            staff_count = cur.fetchone()['count']
            print(f"\n👥 Сотрудников в правильной базе: {staff_count}")
            
            if staff_count > 0:
                cur.execute("SELECT unique_code, full_name FROM staff WHERE status = 'active'")
                active_staff = cur.fetchall()
                
                print("📋 Активные сотрудники:")
                for staff in active_staff:
                    print(f"  • {staff['full_name']} → {staff['unique_code']}")
            else:
                print("❌ В правильной базе данных НЕТ сотрудников!")
        else:
            print("❌ Таблица staff НЕ существует в правильной базе!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке правильной базы: {e}")

def copy_staff_data():
    """Копирует данные сотрудников из bot_database.db в evgenich_data.db"""
    print("\n📋 КОПИРОВАНИЕ ДАННЫХ СОТРУДНИКОВ")
    print("=" * 50)
    
    source_db = "bot_database.db"
    target_db = os.path.join("data", "evgenich_data.db")
    
    if not os.path.exists(source_db):
        print(f"❌ Исходная база {source_db} не найдена")
        return
    
    try:
        # Читаем данные из исходной базы
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row
        source_cur = source_conn.cursor()
        
        source_cur.execute("SELECT * FROM staff")
        staff_data = source_cur.fetchall()
        
        print(f"📊 Найдено {len(staff_data)} сотрудников в исходной базе")
        
        # Создаем целевую базу, если не существует
        target_conn = sqlite3.connect(target_db)
        target_cur = target_conn.cursor()
        
        # Создаем таблицу staff
        target_cur.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                short_name TEXT NOT NULL,
                unique_code TEXT UNIQUE NOT NULL,
                position TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                telegram_id INTEGER UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Очищаем целевую таблицу
        target_cur.execute("DELETE FROM staff")
        
        # Копируем данные
        for staff in staff_data:
            target_cur.execute("""
                INSERT INTO staff (staff_id, full_name, short_name, unique_code, position, status, telegram_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                staff['staff_id'],
                staff['full_name'], 
                staff['short_name'],
                staff['unique_code'],
                staff['position'],
                staff['status'],
                staff['telegram_id'],
                staff['created_at']
            ))
        
        target_conn.commit()
        
        print(f"✅ Скопировано {len(staff_data)} сотрудников в {target_db}")
        
        # Проверяем результат
        target_cur.execute("SELECT COUNT(*) as count FROM staff")
        copied_count = target_cur.fetchone()[0]
        print(f"✅ Проверка: {copied_count} сотрудников в целевой базе")
        
        source_conn.close()
        target_conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при копировании: {e}")

if __name__ == "__main__":
    test_correct_database()
    
    # Предлагаем скопировать данные если нужно
    response = input("\nСкопировать данные сотрудников из bot_database.db? (y/n): ")
    if response.lower() == 'y':
        copy_staff_data()
        print("\n" + "="*50)
        test_correct_database()  # Проверяем еще раз
