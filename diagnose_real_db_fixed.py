#!/usr/bin/env python3
"""
Исправленная диагностика реальной базы данных
"""

import sqlite3

def check_real_database_fixed():
    """Проверяет реальную базу данных bot_database.db"""
    print("🔍 ДИАГНОСТИКА РЕАЛЬНОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cur = conn.cursor()
        
        # Проверяем данные сотрудников
        cur.execute("SELECT COUNT(*) FROM staff")
        staff_count = cur.fetchone()[0]
        print(f"👥 Всего сотрудников в базе: {staff_count}")
        
        if staff_count > 0:
            cur.execute("SELECT * FROM staff ORDER BY staff_id")
            staff_list = cur.fetchall()
            
            print("\n👥 Список всех сотрудников:")
            for staff in staff_list:
                staff_id, full_name, short_name, unique_code, position, status, telegram_id, created_at = staff
                print(f"  • ID: {staff_id}")
                print(f"    Имя: {full_name}")
                print(f"    Код: {unique_code}")
                print(f"    Статус: {status}")
                print(f"    Telegram ID: {telegram_id if telegram_id else 'НЕТ'}")
                print(f"    Должность: {position}")
                print()
        
        # Проверяем пользователей
        cur.execute("SELECT COUNT(*) FROM users")
        users_count = cur.fetchone()[0]
        print(f"👤 Всего пользователей: {users_count}")
        
        if users_count > 0:
            # Последние пользователи
            cur.execute("""
                SELECT user_id, source, brought_by_staff_id 
                FROM users 
                ORDER BY rowid DESC 
                LIMIT 10
            """)
            recent_users = cur.fetchall()
            
            print("\n📱 Последние 10 пользователей:")
            for user in recent_users:
                user_id, source, brought_by_staff_id = user
                print(f"  • ID: {user_id}")
                print(f"    Источник: {source}")
                print(f"    Сотрудник ID: {brought_by_staff_id if brought_by_staff_id else 'НЕТ'}")
                print()
        
        # Статистика по источникам
        cur.execute("""
            SELECT source, COUNT(*) as count
            FROM users
            GROUP BY source
            ORDER BY count DESC
        """)
        source_stats = cur.fetchall()
        
        print("📊 Статистика по источникам:")
        for source, count in source_stats:
            print(f"  • {source}: {count} чел.")
        
        # Пользователи, привлеченные сотрудниками
        cur.execute("""
            SELECT COUNT(*) 
            FROM users 
            WHERE brought_by_staff_id IS NOT NULL
        """)
        staff_referred = cur.fetchone()[0]
        print(f"\n🎯 Пользователей, привлеченных сотрудниками: {staff_referred}")
        
        conn.close()
        
        # Анализ проблемы
        print("\n" + "="*50)
        print("🔎 АНАЛИЗ ПРОБЛЕМЫ:")
        
        if staff_count > 0:
            conn = sqlite3.connect('bot_database.db')
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM staff WHERE telegram_id IS NOT NULL")
            real_staff = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM staff WHERE telegram_id IS NULL")
            fake_staff = cur.fetchone()[0]
            
            print(f"  • Реальных сотрудников (с Telegram ID): {real_staff}")
            print(f"  • Тестовых сотрудников (без Telegram ID): {fake_staff}")
            
            if real_staff == 0:
                print("  ❌ ПРОБЛЕМА: Нет реальных сотрудников!")
                print("  💡 РЕШЕНИЕ: Сотрудники должны использовать команду /staff_reg")
            
            conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")

if __name__ == "__main__":
    check_real_database_fixed()
