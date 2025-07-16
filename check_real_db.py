#!/usr/bin/env python3
"""
Диагностика реальной базы данных сотрудников без зависимостей от config
"""

import sqlite3
import os

def check_real_staff():
    """Проверяет реальных сотрудников в базе данных."""
    db_path = 'bot_database.db'
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("🔍 ПРОВЕРКА РЕАЛЬНОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Проверяем таблицу staff
    try:
        cur.execute("SELECT * FROM staff")
        staff_data = cur.fetchall()
        
        if staff_data:
            print(f"👥 Найдено сотрудников: {len(staff_data)}")
            print()
            
            # Получаем названия колонок
            cur.execute("PRAGMA table_info(staff)")
            columns = [col[1] for col in cur.fetchall()]
            
            for row in staff_data:
                staff_dict = dict(zip(columns, row))
                print(f"👤 {staff_dict.get('full_name', 'N/A')} ({staff_dict.get('position', 'N/A')})")
                print(f"   ID: {staff_dict.get('staff_id', 'N/A')}")
                print(f"   Код: {staff_dict.get('unique_code', 'N/A')}")
                print(f"   Статус: {staff_dict.get('status', 'N/A')}")
                print(f"   Telegram ID: {staff_dict.get('telegram_id', 'N/A')}")
                print(f"   QR-ссылка: https://t.me/EvgenichTapBarBot?start=w_{staff_dict.get('unique_code', 'N/A')}")
                print()
        else:
            print("❌ В базе нет ни одного реального сотрудника!")
            print("💡 Сотрудникам нужно зарегистрироваться через /staff_reg в рабочем чате")
    
    except sqlite3.Error as e:
        print(f"❌ Ошибка при проверке таблицы staff: {e}")
    
    # Проверяем последние переходы пользователей
    print("\n" + "=" * 50)
    print("📊 ПОСЛЕДНИЕ ПЕРЕХОДЫ ПОЛЬЗОВАТЕЛЕЙ:")
    
    try:
        cur.execute("""
            SELECT user_id, source, brought_by_staff_id, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_users = cur.fetchall()
        
        if recent_users:
            for user in recent_users:
                user_id, source, staff_id, created_at = user
                if staff_id:
                    print(f"✅ Пользователь {user_id}: {source} (привел сотрудник ID: {staff_id}) - {created_at}")
                else:
                    print(f"❌ Пользователь {user_id}: {source} (без сотрудника) - {created_at}")
        else:
            print("❌ Нет данных о пользователях")
            
    except sqlite3.Error as e:
        print(f"❌ Ошибка при проверке пользователей: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_real_staff()
