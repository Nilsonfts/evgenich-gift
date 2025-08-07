#!/usr/bin/env python3
# coding: utf-8

import psycopg2

# Подключаемся к базе данных
conn = psycopg2.connect(
    "postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway"
)
cur = conn.cursor()

# Получаем структуру таблицы users
cur.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
""")

# Выводим результаты
print("Структура таблицы users:")
print("-" * 50)
for col in cur.fetchall():
    name = col[0]
    data_type = col[1]
    max_length = col[2]
    
    if max_length:
        print(f"{name}: {data_type}({max_length})")
    else:
        print(f"{name}: {data_type}")

# Закрываем соединение
cur.close()
conn.close()
