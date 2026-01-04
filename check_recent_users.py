#!/usr/bin/env python3
"""Проверить, когда в последний раз добавлялись пользователи."""
import psycopg2
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL не установлена")
    exit(1)

try:
    import psycopg2
    from urllib.parse import urlparse
    
    parsed = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/')
    )
    cur = conn.cursor()
    
    print("🔍 ПРОВЕРКА: Когда последний раз добавлялись пользователи")
    print("=" * 70)
    
    # Последние 20 пользователей (если есть дата регистрации)
    cur.execute("""
        SELECT user_id, first_name, status, created_at 
        FROM users 
        ORDER BY created_at DESC 
        LIMIT 20
    """)
    
    results = cur.fetchall()
    
    if results:
        print("\n📋 Последние 20 пользователей (по created_at):")
        for user_id, first_name, status, created_at in results:
            time_ago = "?"
            if created_at:
                delta = datetime.utcnow() - created_at.replace(tzinfo=None)
                if delta.days > 0:
                    time_ago = f"{delta.days} дн назад"
                else:
                    hours = delta.total_seconds() / 3600
                    if hours > 1:
                        time_ago = f"{int(hours)} ч назад"
                    else:
                        mins = delta.total_seconds() / 60
                        time_ago = f"{int(mins)} м назад"
            
            print(f"   {user_id:12} | {first_name:20} | {status:15} | {created_at} ({time_ago})")
    else:
        print("\n❌ Не найдены пользователи с created_at!")
    
    # Альтернативный способ - через id (если created_at не заполнен)
    print("\n" + "=" * 70)
    print("📋 Если выше не было результатов, проверим по ID (самые большие ID - самые новые):")
    
    cur.execute("""
        SELECT user_id, first_name, status 
        FROM users 
        ORDER BY user_id DESC 
        LIMIT 10
    """)
    
    results = cur.fetchall()
    if results:
        for user_id, first_name, status in results:
            print(f"   {user_id:12} | {first_name:20} | {status:15}")
    
    # Посчитаем, сколько пользователей в каждом статусе за последний месяц
    print("\n" + "=" * 70)
    print("📊 Статистика по датам создания:")
    
    cur.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count,
            COUNT(CASE WHEN status = 'redeemed' THEN 1 END) as redeemed
        FROM users
        WHERE created_at IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    """)
    
    results = cur.fetchall()
    if results:
        print("   Дата       | Всего | Выполнено")
        print("   " + "-" * 40)
        for date, count, redeemed in results:
            print(f"   {date} | {count:5} | {redeemed:5}")
    else:
        print("   ❌ Нет данных по датам (created_at может быть NULL)")
    
    # Проверим, есть ли NULL даты
    print("\n" + "=" * 70)
    print("🔍 Техническая информация:")
    
    cur.execute("SELECT COUNT(*) FROM users WHERE created_at IS NULL")
    null_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM users WHERE created_at IS NOT NULL")
    not_null_count = cur.fetchone()[0]
    
    print(f"   Пользователей с NULL created_at: {null_count}")
    print(f"   Пользователей с заполненной created_at: {not_null_count}")
    
    if null_count > 0:
        print(f"\n⚠️  Много пользователей без даты! Возможно, created_at не заполняется")
    
    conn.close()
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
