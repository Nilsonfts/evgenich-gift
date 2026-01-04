#!/usr/bin/env python3
"""
Скрипт для получения статистики пользователей.
Использует переменные окружения из .env или позволяет подключиться к любому PostgreSQL.
"""
import os
import psycopg2
from urllib.parse import urlparse

def connect_postgres(db_url):
    """Подключиться к PostgreSQL."""
    try:
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None

def get_stats(conn):
    """Получить и вывести статистику."""
    if not conn:
        return
    
    cur = conn.cursor()
    
    print("\n📊 СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ (PostgreSQL)")
    print("=" * 70)
    
    try:
        # Общее количество
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]
        print(f"\n👥 Всего пользователей в боте: {total}")
        
        if total == 0:
            print("   (данных нет)")
            return
        
        # По статусам
        cur.execute("SELECT status, COUNT(*) as cnt FROM users GROUP BY status ORDER BY cnt DESC")
        statuses = cur.fetchall()
        print("\n📌 По статусам:")
        for status, count in statuses:
            pct = (count / total * 100)
            bar = "█" * int(pct / 2)
            print(f"   {status:20} {count:5} ({pct:5.1f}%) {bar}")
        
        # По источникам
        cur.execute("SELECT source, COUNT(*) as cnt FROM users GROUP BY source ORDER BY cnt DESC")
        sources = cur.fetchall()
        print("\n📍 По источникам:")
        for source, count in sources:
            pct = (count / total * 100)
            print(f"   {source:20} {count:5} ({pct:5.1f}%)")
        
        # По сотрудникам
        cur.execute("SELECT brought_by_staff_id, COUNT(*) as cnt FROM users WHERE brought_by_staff_id IS NOT NULL GROUP BY brought_by_staff_id ORDER BY cnt DESC LIMIT 10")
        staff = cur.fetchall()
        if staff:
            print("\n👨‍💼 Пригласили сотрудники (топ-10):")
            for staff_id, count in staff:
                print(f"   Сотрудник {staff_id}: {count}")
        
        # По рефералам
        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL")
        referred = cur.fetchone()[0]
        ref_pct = (referred / total * 100)
        print(f"\n🔗 По реферальным ссылкам: {referred} ({ref_pct:.1f}%)")
        
        # Статус "redeemed"
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed'")
        redeemed = cur.fetchone()[0]
        red_pct = (redeemed / total * 100)
        print(f"✅ Получили настойку (redeemed): {redeemed} ({red_pct:.1f}%)")
        
        # Даты
        cur.execute("SELECT MIN(signup_date), MAX(signup_date) FROM users")
        dates = cur.fetchone()
        if dates and dates[0]:
            print(f"\n📅 Период:")
            print(f"   Первый пользователь: {dates[0]}")
            print(f"   Последний пользователь: {dates[1]}")
        
        # Среднее время на выполнение
        cur.execute("""
            SELECT AVG(EXTRACT(EPOCH FROM (redeem_date - signup_date)) / 3600)
            FROM users WHERE redeem_date IS NOT NULL
        """)
        avg_hours = cur.fetchone()[0]
        if avg_hours:
            print(f"   Среднее время до выполнения: {avg_hours:.1f} часов")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
    finally:
        cur.close()

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ DATABASE_URL не установлена в .env")
        print("\nИспользование:")
        print("  DATABASE_URL=postgresql://user:pass@host/db python3 pg_stats.py")
        exit(1)
    
    print(f"🔌 Подключаюсь к БД...")
    conn = connect_postgres(db_url)
    if conn:
        get_stats(conn)
        conn.close()
        print("\n✅ Готово!")
