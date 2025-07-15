#!/usr/bin/env python3
import database
import datetime
import pytz

print("🔍 Диагностика базы данных...")

# Инициализируем базу
database.init_db()

conn = database.get_db_connection()
cur = conn.cursor()

# Проверяем структуру таблицы users
cur.execute("PRAGMA table_info(users)")
columns = cur.fetchall()
print("Колонки в таблице users:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Проверяем данные
cur.execute("SELECT COUNT(*) FROM users")
total = cur.fetchone()[0]
print(f"\nВсего пользователей: {total}")

if total > 0:
    # Проверяем статусы
    cur.execute("SELECT status, COUNT(*) FROM users GROUP BY status")
    statuses = cur.fetchall()
    print("\nСтатусы пользователей:")
    for row in statuses:
        print(f"  {row[0]}: {row[1]}")
    
    # Проверяем источники
    cur.execute("SELECT source, COUNT(*) FROM users GROUP BY source")
    sources = cur.fetchall()
    print("\nИсточники пользователей:")
    for row in sources:
        print(f"  {row[0] or 'Null'}: {row[1]}")

# Добавляем тестовых пользователей если их нет
if total == 0:
    print("\n📝 Добавляем тестовых пользователей...")
    now = datetime.datetime.now(pytz.utc)
    test_data = [
        (200001, 'test1', 'Тестовый1', 'Телеграм', 'redeemed_and_left', now - datetime.timedelta(days=5)),
        (200002, 'test2', 'Тестовый2', 'QR-код', 'redeemed_and_left', now - datetime.timedelta(days=3)),
        (200003, 'test3', 'Тестовый3', 'Реферал', 'redeemed', now - datetime.timedelta(days=1)),
        (200004, 'test4', 'Тестовый4', 'Телеграм', 'issued', now - datetime.timedelta(hours=12)),
    ]
    
    for data in test_data:
        cur.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, source, status, signup_date) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)
    
    conn.commit()
    print("✅ Тестовые данные добавлены")

# Теперь тестируем запросы из reports_callbacks
print("\n🧪 Тестируем запросы отчетов...")

# Анализ оттока по источникам
end_time = datetime.datetime.now(pytz.utc)
start_time = end_time - datetime.timedelta(days=30)

cur.execute("""
    SELECT source, COUNT(*) as cnt 
    FROM users 
    WHERE status = 'redeemed_and_left' 
    GROUP BY source
""")
churn_data = cur.fetchall()

print("\n📈 Анализ оттока по источникам:")
if churn_data:
    total_churn = sum(row[1] for row in churn_data)
    for row in churn_data:
        percent = round(row[1] / total_churn * 100, 1) if total_churn else 0
        print(f"  • {row[0] or 'Неизвестно'}: {row[1]} ({percent}%)")
else:
    print("  ❌ Нет данных по оттоку")

# Пики активности
cur.execute("""
    SELECT strftime('%H', signup_date) as hour, COUNT(*) as cnt 
    FROM users 
    WHERE signup_date BETWEEN ? AND ? 
    GROUP BY hour 
    ORDER BY hour
""", (start_time, end_time))
activity_data = cur.fetchall()

print("\n🕒 Пики активности:")
if activity_data:
    for row in activity_data:
        print(f"  • {row[0]}:00 — {row[1]}")
else:
    print("  ❌ Нет данных по активности")

conn.close()
print("\n✅ Диагностика завершена")
