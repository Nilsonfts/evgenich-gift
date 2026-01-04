#!/usr/bin/env python3
"""Получить статистику по пользователям из SQLite БД."""
import sqlite3
import os

DB_PATH = os.getenv("DATABASE_PATH", "bot.db")

if not os.path.exists(DB_PATH):
    print(f"❌ База данных не найдена: {DB_PATH}")
    exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("📊 СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ (SQLite)")
    print("=" * 60)
    
    # Общее количество пользователей
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    print(f"\n👥 Всего пользователей в боте: {total_users}")
    
    # По статусам
    cur.execute("SELECT status, COUNT(*) as cnt FROM users GROUP BY status ORDER BY cnt DESC")
    statuses = cur.fetchall()
    
    if statuses:
        print("\n📌 Распределение по статусам:")
        for status, count in statuses:
            pct = (count / total_users * 100) if total_users > 0 else 0
            print(f"   {status:15} : {count:4} ({pct:5.1f}%)")
    
    # По источникам
    cur.execute("SELECT source, COUNT(*) as cnt FROM users GROUP BY source ORDER BY cnt DESC")
    sources = cur.fetchall()
    
    if sources:
        print("\n📍 По источникам регистрации:")
        for source, count in sources:
            pct = (count / total_users * 100) if total_users > 0 else 0
            print(f"   {source:15} : {count:4} ({pct:5.1f}%)")
    
    # По сотрудникам (которые пригласили)
    cur.execute("SELECT brought_by_staff_id, COUNT(*) as cnt FROM users WHERE brought_by_staff_id IS NOT NULL GROUP BY brought_by_staff_id ORDER BY cnt DESC")
    staff = cur.fetchall()
    
    if staff:
        print("\n👨‍💼 Пользователи, пригласённые сотрудниками (топ):")
        for staff_id, count in staff[:10]:
            print(f"   Сотрудник {staff_id}: {count}")
    
    # По рефералам
    cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL")
    referred = cur.fetchone()[0]
    ref_pct = (referred / total_users * 100) if total_users > 0 else 0
    print(f"\n🔗 Пришли по реферальной ссылке: {referred} ({ref_pct:.1f}%)")
    
    # Первый и последний пользователь
    cur.execute("SELECT MIN(signup_date), MAX(signup_date) FROM users")
    dates = cur.fetchone()
    if dates and dates[0]:
        print(f"\n📅 Диапазон регистраций:")
        print(f"   Первый: {dates[0]}")
        print(f"   Последний: {dates[1]}")
    
    conn.close()
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
