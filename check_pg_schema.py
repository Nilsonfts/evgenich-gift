import psycopg2

# Параметры подключения к PostgreSQL
db_url = "postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway"

# Подключение к базе данных
conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# Выполнение запроса для получения структуры таблицы users
cursor.execute("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;
""")

# Получение результатов
results = cursor.fetchall()

print("Структура таблицы users в PostgreSQL:")
for row in results:
    print(f"- {row[0]} ({row[1]})")

# Закрытие соединения
cursor.close()
conn.close()
