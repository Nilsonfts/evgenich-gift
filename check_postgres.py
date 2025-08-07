import psycopg2

# Параметры подключения к PostgreSQL
db_url = "postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway"

# Подключение к базе данных
conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# Выполнение запроса
cursor.execute("SELECT COUNT(*) FROM users;")
result = cursor.fetchone()

print(f"Количество записей в таблице users в PostgreSQL: {result[0]}")

# Закрытие соединения
cursor.close()
conn.close()
