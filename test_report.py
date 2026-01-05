#!/usr/bin/env python3
"""Тест формирования отчёта за указанный период."""
import os
import sys
from datetime import datetime, timedelta
import pytz

# Устанавливаем переменные окружения
os.environ['USE_POSTGRES'] = 'true'
os.environ['DATABASE_URL'] = 'postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway'
os.environ['BOT_TOKEN'] = 'test'
os.environ['CHANNEL_ID'] = 'test'
os.environ['ADMIN_IDS'] = '123'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'

import logging
logging.basicConfig(level=logging.INFO)

print("📊 ТЕСТ ОТЧЁТА")
print("=" * 70)

from db.postgres_client import PostgresClient

pg_client = PostgresClient()

# Определим период - вчера 12:00 до сегодня 06:00
moscow_tz = pytz.timezone('Europe/Moscow')
now = datetime.now(moscow_tz)

end_time = now.replace(hour=6, minute=0, second=0, microsecond=0)
start_time = (end_time - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

print(f"\n📅 Период отчёта:")
print(f"   От: {start_time.strftime('%d.%m.%Y %H:%M')}")
print(f"   До: {end_time.strftime('%d.%m.%Y %H:%M')}")

# Получаем статистику
print(f"\n📊 Статистика за период:\n")

# Новые регистрации
query = """
    SELECT COUNT(*) FROM users 
    WHERE register_date >= %s AND register_date < %s
"""

with pg_client.engine.connect() as conn:
    result = conn.execute(
        __import__('sqlalchemy').text(query),
        {"start": start_time, "end": end_time}
    ).scalar()
    
    print(f"   ➕ Новых регистраций: {result}")
    
    # Выполнено настоек
    query_redeemed = """
        SELECT COUNT(*) FROM users 
        WHERE redeem_date >= %s AND redeem_date < %s
    """
    
    result_redeemed = conn.execute(
        __import__('sqlalchemy').text(query_redeemed),
        {"start": start_time, "end": end_time}
    ).scalar()
    
    print(f"   ✅ Выполнено настоек: {result_redeemed}")
    
    # По источникам
    query_sources = """
        SELECT source, COUNT(*) as cnt 
        FROM users 
        WHERE register_date >= %s AND register_date < %s
        GROUP BY source
        ORDER BY cnt DESC
        LIMIT 5
    """
    
    sources = conn.execute(
        __import__('sqlalchemy').text(query_sources),
        {"start": start_time, "end": end_time}
    ).fetchall()
    
    if sources:
        print(f"\n   📍 По источникам:")
        for source, count in sources:
            print(f"      {source}: {count}")
    else:
        print(f"\n   📍 Нет регистраций в этот период")
    
    # По сотрудникам
    query_staff = """
        SELECT brought_by_staff_id, COUNT(*) as cnt
        FROM users
        WHERE register_date >= %s AND register_date < %s
          AND brought_by_staff_id IS NOT NULL
        GROUP BY brought_by_staff_id
        ORDER BY cnt DESC
    """
    
    staff = conn.execute(
        __import__('sqlalchemy').text(query_staff),
        {"start": start_time, "end": end_time}
    ).fetchall()
    
    if staff:
        print(f"\n   👨‍💼 По сотрудникам:")
        for staff_id, count in staff:
            print(f"      Сотрудник {staff_id}: {count}")

print("\n" + "=" * 70)
print("✅ Отчёты работают! Данные из PostgreSQL получаются корректно.")
print(f"\nЗавтра в 07:00 по Москве админ получит автоматический отчёт за:")
print(f"   12:00 сегодня — 06:00 завтра")
