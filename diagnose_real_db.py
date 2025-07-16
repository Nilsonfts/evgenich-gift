#!/usr/bin/env python3
"""
Диагностика реальной базы данных для поиска проблемы с QR-кодами сотрудников
"""

import sqlite3
import sys

def check_real_database():
    """Проверяет реальную базу данных bot_database.db"""
    print("🔍 ДИАГНОСТИКА РЕАЛЬНОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Проверяем структуру таблицы staff
        print("📋 Структура таблицы staff:")
        cur.execute("PRAGMA table_info(staff)")
        staff_columns = cur.fetchall()
        for col in staff_columns:
            print(f"  • {col['name']}: {col['type']}")
        
        print("\n" + "-" * 30)
        
        # Проверяем данные сотрудников
        cur.execute("SELECT COUNT(*) as count FROM staff")
        staff_count = cur.fetchone()['count']
        print(f"👥 Всего сотрудников в базе: {staff_count}")
        
        if staff_count > 0:
            cur.execute("SELECT * FROM staff ORDER BY staff_id")
            staff_list = cur.fetchall()
            
            print("\n👥 Список всех сотрудников:")
            for staff in staff_list:
                print(f"  • ID: {staff['staff_id']}")
                print(f"    Имя: {staff['full_name']}")
                print(f"    Код: {staff['unique_code']}")
                print(f"    Статус: {staff['status']}")
                print(f"    Telegram ID: {staff.get('telegram_id', 'НЕТ')}")
                print(f"    Должность: {staff.get('position', 'НЕТ')}")
                print()
        
        print("-" * 30)
        
        # Проверяем структуру таблицы users
        print("\n📋 Структура таблицы users:")
        cur.execute("PRAGMA table_info(users)")
        user_columns = cur.fetchall()
        for col in user_columns:
            print(f"  • {col['name']}: {col['type']}")
        
        # Проверяем последних пользователей
        cur.execute("SELECT COUNT(*) as count FROM users")
        users_count = cur.fetchone()['count']
        print(f"\n👤 Всего пользователей: {users_count}")
        
        if users_count > 0:
            cur.execute("""
                SELECT user_id, source, brought_by_staff_id, created_at 
                FROM users 
                ORDER BY rowid DESC 
                LIMIT 10
            """)
            recent_users = cur.fetchall()
            
            print("\n📱 Последние 10 пользователей:")
            for user in recent_users:
                print(f"  • ID: {user['user_id']}")
                print(f"    Источник: {user['source']}")
                print(f"    Сотрудник ID: {user.get('brought_by_staff_id', 'НЕТ')}")
                print(f"    Дата: {user.get('created_at', 'НЕТ')}")
                print()
        
        # Проверяем связи пользователей с сотрудниками
        cur.execute("""
            SELECT u.source, COUNT(*) as count
            FROM users u
            GROUP BY u.source
            ORDER BY count DESC
        """)
        source_stats = cur.fetchall()
        
        print("-" * 30)
        print("\n📊 Статистика по источникам:")
        for stat in source_stats:
            print(f"  • {stat['source']}: {stat['count']} чел.")
        
        # Ищем пользователей, привлеченных сотрудниками
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE brought_by_staff_id IS NOT NULL
        """)
        staff_referred = cur.fetchone()['count']
        print(f"\n🎯 Пользователей, привлеченных сотрудниками: {staff_referred}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")

def test_staff_lookup():
    """Тестирует поиск сотрудников по кодам"""
    print("\n🧪 ТЕСТ ПОИСКА СОТРУДНИКОВ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Получаем все активные коды
        cur.execute("SELECT unique_code FROM staff WHERE status = 'active'")
        codes = [row['unique_code'] for row in cur.fetchall()]
        
        print(f"📋 Найдено активных кодов: {len(codes)}")
        
        for code in codes:
            # Тестируем поиск по каждому коду
            cur.execute("""
                SELECT staff_id, full_name, short_name, unique_code, status
                FROM staff 
                WHERE unique_code = ? AND status = 'active'
            """, (code,))
            
            result = cur.fetchone()
            if result:
                print(f"  ✅ Код '{code}' → {result['full_name']}")
            else:
                print(f"  ❌ Код '{code}' не найден")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании поиска: {e}")

if __name__ == "__main__":
    check_real_database()
    test_staff_lookup()
