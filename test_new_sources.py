#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новых источников трафика.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_new_sources():
    """Тестирует новые источники трафика."""
    print("🧪 Тестирование новых источников трафика...")
    
    try:
        # Создаем директорию data если её нет
        if not os.path.exists('data'):
            os.makedirs('data')
            print("✅ Создана директория data")

        # Инициализируем базу данных
        import sqlite3
        from datetime import datetime, timedelta
        from config import DATABASE_PATH

        db_path = DATABASE_PATH
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Создаем таблицу users с нужными полями
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                status TEXT DEFAULT 'registered',
                source TEXT DEFAULT 'direct',
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeem_date TIMESTAMP,
                referrer_id INTEGER,
                brought_by_staff_id INTEGER
            )
        """)

        # Новые источники из списка ТГ бота
        new_sources_data = [
            (10001, "Максим", "maxim_tv", "issued", "QR-код на ТВ"),
            (10002, "Светлана", "sveta_bar", "redeemed", "QR-код на баре"), 
            (10003, "Денис", "denis_waiter", "issued", "QR от официанта"),
            (10004, "Олеся", "olesya_vk", "redeemed", "Ссылка из ВКонтакте"),
            (10005, "Николай", "nick_inst", "issued", "Ссылка из Instagram"),
            (10006, "Катя", "katya_menu", "redeemed", "Меню в баре"),
            (10007, "Роман", "roman_flyer", "issued", "Листовка на улице"),
            (10008, "Ирина", "ira_street", "redeemed", "Уличное Меню"),
            (10009, "Сергей", "sergey_2gis", "issued", "2ГИС Кнопка"),
            (10010, "Юлия", "yulia_site", "redeemed", "Кнопка Сайт"),
            (10011, "Андрей", "andrey_taplink", "issued", "Таплинк на ТВ"),
        ]

        base_date = datetime.now()

        # Очищаем тестовые данные из предыдущего запуска
        cur.execute("DELETE FROM users WHERE user_id >= 10000")

        for i, (user_id, first_name, username, status, source) in enumerate(new_sources_data):
            signup_date = base_date - timedelta(days=len(new_sources_data)-i)
            redeem_date = signup_date + timedelta(hours=2) if status == "redeemed" else None
            
            cur.execute("""
                INSERT INTO users 
                (user_id, first_name, username, status, source, signup_date, redeem_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, first_name, username, status, source, signup_date, redeem_date))

        conn.commit()
        print(f"✅ Добавлено {len(new_sources_data)} тестовых пользователей с новыми источниками")

        # Тестируем отчет
        print("\n📊 Тестирование отчета по источникам...")
        
        # Имитируем функцию get_report_data_for_period
        start_time = base_date - timedelta(days=30)
        end_time = base_date + timedelta(days=1)
        
        # Подсчет выданных купонов
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE signup_date BETWEEN ? AND ? 
            AND status IN ('issued', 'redeemed', 'redeemed_and_left')
        """, (start_time, end_time))
        issued_count = cur.fetchone()[0]
        
        # Подсчет погашенных купонов
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE redeem_date BETWEEN ? AND ?
        """, (start_time, end_time))
        redeemed_count = cur.fetchone()[0]
        
        # Статистика по источникам
        cur.execute("""
            SELECT source, COUNT(*) FROM users 
            WHERE signup_date BETWEEN ? AND ? 
            GROUP BY source 
            ORDER BY COUNT(*) DESC
        """, (start_time, end_time))
        sources_stats = dict(cur.fetchall())
        
        conn.close()
        
        print(f"\n📈 Результаты тестирования:")
        print(f"   Выдано купонов: {issued_count}")
        print(f"   Погашено купонов: {redeemed_count}")
        print(f"   Конверсия: {round((redeemed_count/issued_count)*100, 1) if issued_count > 0 else 0}%")
        
        print(f"\n📍 Статистика по источникам:")
        for source, count in sources_stats.items():
            print(f"   • {source}: {count}")
        
        print(f"\n✅ Тестирование завершено успешно!")
        
        # Тестируем экспорт в Google Sheets (симуляция)
        print(f"\n📄 Симуляция экспорта в Google Sheets...")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT user_id, first_name, username, status, source, signup_date, redeem_date
            FROM users 
            WHERE user_id >= 10000
            ORDER BY signup_date DESC
        """)
        
        users = cur.fetchall()
        conn.close()
        
        print(f"Данные для экспорта ({len(users)} пользователей):")
        print(f"ID | Имя | Username | Статус | Источник | Регистрация")
        print("-" * 80)
        
        for user in users:
            signup_str = user['signup_date'][:16] if user['signup_date'] else "н/д"
            print(f"{user['user_id']} | {user['first_name']} | @{user['username']} | {user['status']} | {user['source']} | {signup_str}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_new_sources()
    if success:
        print("\n🎉 Все тесты прошли успешно!")
    else:
        print("\n💥 Обнаружены ошибки!")
        sys.exit(1)
