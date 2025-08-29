import os
import psycopg2

# Исправление PostgreSQL collation
try:
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('❌ DATABASE_URL не найден')
        exit(1)
    
    print('🔌 Подключаемся к PostgreSQL...')
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    print('🔧 Обновляем версию collation...')
    cur.execute('ALTER DATABASE railway REFRESH COLLATION VERSION;')
    
    print('✅ Версия collation успешно обновлена!')
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Ошибка: {e}')
    exit(1)
