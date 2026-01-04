#!/usr/bin/env python3
"""Быстрая проверка последнего добавленного пользователя."""
import psycopg2
from urllib.parse import urlparse
import os
from datetime import datetime

DATABASE_URL = "postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway"

parsed = urlparse(DATABASE_URL)
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port or 5432,
    user=parsed.username,
    password=parsed.password,
    database=parsed.path.lstrip('/')
)
cur = conn.cursor()

print("🔍 Последний добавленный пользователь:\n")

cur.execute("""
    SELECT user_id, first_name, username, status, register_date, source
    FROM users 
    WHERE register_date IS NOT NULL
    ORDER BY register_date DESC 
    LIMIT 1
""")

result = cur.fetchone()
if result:
    user_id, first_name, username, status, register_date, source = result
    
    now = datetime.utcnow()
    delta = now - register_date.replace(tzinfo=None) if register_date else None
    
    seconds = int(delta.total_seconds()) if delta else 0
    if seconds < 60:
        time_ago = f"{seconds} сек назад ⚡"
    elif seconds < 3600:
        time_ago = f"{seconds // 60} мин назад"
    else:
        time_ago = f"{seconds // 3600} ч назад"
    
    print(f"👤 {first_name} (@{username if username else '?'})")
    print(f"🆔 User ID: {user_id}")
    print(f"📊 Статус: {status}")
    print(f"📍 Источник: {source}")
    print(f"📅 Добавлен: {register_date}")
    print(f"⏰ Это было: {time_ago}")
    
    if seconds < 120:
        print(f"\n✅ СВЕЖИЙ! Бот работает! 🎉")
    elif seconds < 86400:
        print(f"\n✅ Недавно добавлен")
    else:
        days = seconds // 86400
        print(f"\n⚠️  Старый пользователь ({days} дней назад)")

conn.close()
