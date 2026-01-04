#!/usr/bin/env python3
"""Получить статистику по пользователям из БД."""
import sqlite3
import sys
from core.config import DATABASE_PATH, USE_POSTGRES

if USE_POSTGRES:
    from db.postgres_client import PostgresClient
    print("📊 СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ (PostgreSQL)")
    print("=" * 50)
    try:
        pg_client = PostgresClient()
        
        # Общее количество пользователей
        result = pg_client.conn.execute("SELECT COUNT(*) FROM users").fetchone()
        total_users = result[0] if result else 0
        
        # По статусам
        statuses = pg_client.conn.execute(
            "SELECT status, COUNT(*) FROM users GROUP BY status ORDER BY COUNT(*) DESC"
        ).fetchall()
        
        # По источникам
        sources = pg_client.conn.execute(
            "SELECT source, COUNT(*) FROM users GROUP BY source ORDER BY COUNT(*) DESC"
        ).fetchall()
        
        print(f"\n👥 Всего пользователей: {total_users}")
        
        print("\n📌 По статусам:")
        for status, count in statuses:
            print(f"   {status}: {count}")
        
        print("\n📍 По источникам:")
        for source, count in sources:
            print(f"   {source}: {count}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        sys.exit(1)
else:
    print("📊 СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ (SQLite)")
    print("=" * 50)
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        
        # Общее количество пользователей
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        # По статусам
        cur.execute("SELECT status, COUNT(*) FROM users GROUP BY status ORDER BY COUNT(*) DESC")
        statuses = cur.fetchall()
        
        # По источникам
        cur.execute("SELECT source, COUNT(*) FROM users GROUP BY source ORDER BY COUNT(*) DESC")
        sources = cur.fetchall()
        
        # По сотрудникам (которые пригласили)
        cur.execute("SELECT brought_by_staff_id, COUNT(*) FROM users WHERE brought_by_staff_id IS NOT NULL GROUP BY brought_by_staff_id ORDER BY COUNT(*) DESC LIMIT 10")
        staff = cur.fetchall()
        
        # По рефералам
        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL")
        referred = cur.fetchone()[0]
        
        conn.close()
        
        print(f"\n👥 Всего пользователей: {total_users}")
        
        print("\n📌 По статусам:")
        for status, count in statuses:
            print(f"   {status}: {count}")
        
        print("\n📍 По источникам:")
        for source, count in sources:
            print(f"   {source}: {count}")
        
        print("\n👨‍💼 Пригласили сотрудники (топ 10):")
        if staff:
            for staff_id, count in staff:
                print(f"   Сотрудник {staff_id}: {count}")
        else:
            print("   Нет данных")
        
        print(f"\n🔗 Пришли по реферальной ссылке: {referred}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

print("\n" + "=" * 50)
