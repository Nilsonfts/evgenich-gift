#!/usr/bin/env python3
"""Тестовый скрипт для проверки добавления пользователя в PostgreSQL."""
import os
import sys
import logging

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Устанавливаем переменные окружения для теста
os.environ['USE_POSTGRES'] = 'true'
os.environ['DATABASE_URL'] = 'postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway'
os.environ['BOT_TOKEN'] = 'test'
os.environ['CHANNEL_ID'] = 'test'
os.environ['ADMIN_IDS'] = '123'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'

print("=" * 70)
print("🧪 ТЕСТИРОВАНИЕ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯ")
print("=" * 70)

# Импортируем после установки переменных
from db.postgres_client import PostgresClient

try:
    print("\n1️⃣ Инициализация PostgresClient...")
    pg_client = PostgresClient()
    print("✅ PostgresClient инициализирован")
    
    print("\n2️⃣ Попытка добавить тестового пользователя...")
    test_user_id = 999888777  # Уникальный ID для теста
    
    result = pg_client.add_new_user(
        user_id=test_user_id,
        username="test_user",
        first_name="Тест",
        source="test_script",
        referrer_id=None,
        brought_by_staff_id=None
    )
    
    if result:
        print(f"✅ Пользователь {test_user_id} успешно добавлен!")
    else:
        print(f"⚠️ Функция вернула False - возможно пользователь уже существует")
    
    print("\n3️⃣ Проверка: ищем добавленного пользователя...")
    import psycopg2
    from urllib.parse import urlparse
    
    db_url = os.environ['DATABASE_URL']
    parsed = urlparse(db_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/')
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_id, first_name, status, register_date 
        FROM users 
        WHERE user_id = %s
    """, (test_user_id,))
    
    user = cur.fetchone()
    
    if user:
        print(f"✅ НАЙДЕН В БД:")
        print(f"   User ID: {user[0]}")
        print(f"   Имя: {user[1]}")
        print(f"   Статус: {user[2]}")
        print(f"   Дата регистрации: {user[3]}")
        print(f"\n🎉 ВСЁ РАБОТАЕТ! Проблема где-то в боте, не в функции add_new_user()")
    else:
        print(f"❌ НЕ НАЙДЕН В БД!")
        print(f"   Проблема в функции add_new_user() - пользователь не сохраняется")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ Тест завершён")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
