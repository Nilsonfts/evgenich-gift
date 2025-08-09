#!/usr/bin/env python3
"""
Миграция PostgreSQL для добавления колонок реферальной системы и рассылок
"""
import os
import sys
import logging
import psycopg2
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def migrate_postgres_columns():
    """Добавляет недостающие колонки в PostgreSQL таблицу users"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        print("💡 Попробуйте установить: export DATABASE_URL='your_postgres_url'")
        return False
    
    try:
        print(f"🔗 Подключение к базе данных...")
        
        # Подключаемся к PostgreSQL
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        print("✅ Подключение установлено")
        print("🔧 Начинаю миграцию PostgreSQL...")
        
        # Проверяем существующие колонки
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND table_schema = 'public'
            ORDER BY column_name;
        """)
        
        existing_columns = [row[0] for row in cur.fetchall()]
        print(f"📋 Найдено {len(existing_columns)} существующих колонок в таблице users")
        
        # Определяем миграции
        migrations = [
            {
                'name': 'referrer_rewarded',
                'sql': 'ALTER TABLE users ADD COLUMN referrer_rewarded BOOLEAN DEFAULT FALSE;',
                'description': 'Флаг получения награды за реферала'
            },
            {
                'name': 'referrer_rewarded_date',
                'sql': 'ALTER TABLE users ADD COLUMN referrer_rewarded_date TIMESTAMP WITH TIME ZONE;',
                'description': 'Дата получения награды за реферала'
            },
            {
                'name': 'blocked',
                'sql': 'ALTER TABLE users ADD COLUMN blocked BOOLEAN DEFAULT FALSE;',
                'description': 'Флаг блокировки пользователя (для рассылок)'
            },
            {
                'name': 'block_date',
                'sql': 'ALTER TABLE users ADD COLUMN block_date TIMESTAMP WITH TIME ZONE;',
                'description': 'Дата блокировки пользователя'
            }
        ]
        
        # Применяем миграции
        applied_count = 0
        for migration in migrations:
            column_name = migration['name']
            if column_name in existing_columns:
                print(f"⏭️  Колонка {column_name} уже существует, пропускаю")
                continue
                
            try:
                cur.execute(migration['sql'])
                print(f"✅ Добавлена колонка {column_name}: {migration['description']}")
                applied_count += 1
            except Exception as e:
                print(f"❌ Ошибка добавления колонки {column_name}: {e}")
                return False
        
        if applied_count > 0:
            # Сохраняем изменения
            conn.commit()
            print(f"💾 Применено {applied_count} миграций")
        else:
            print("ℹ️  Все колонки уже существуют, миграция не требуется")
        
        # Проверяем финальную структуру таблицы
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND table_schema = 'public'
            AND column_name IN ('referrer_rewarded', 'referrer_rewarded_date', 'blocked', 'block_date')
            ORDER BY column_name;
        """)
        
        columns = cur.fetchall()
        if columns:
            print(f"\n📋 Проверка новых колонок:")
            for col_name, data_type, nullable, default in columns:
                default_str = f" DEFAULT {default}" if default else ""
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  • {col_name}: {data_type} {nullable_str}{default_str}")
        
        # Получаем общую статистику таблицы
        cur.execute("SELECT COUNT(*) FROM users;")
        user_count = cur.fetchone()[0]
        print(f"\n📊 Всего пользователей в таблице: {user_count}")
        
        cur.close()
        conn.close()
        
        print(f"\n🎉 Миграция завершена успешно!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Ошибка PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        return False

def check_migration_status():
    """Проверяет статус миграций без их применения"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL не найден")
        return False
        
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Проверяем какие колонки существуют
        required_columns = ['referrer_rewarded', 'referrer_rewarded_date', 'blocked', 'block_date']
        
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND table_schema = 'public'
            AND column_name = ANY(%s)
        """, (required_columns,))
        
        existing = [row[0] for row in cur.fetchall()]
        missing = [col for col in required_columns if col not in existing]
        
        print(f"📋 Status проверки миграций:")
        print(f"  ✅ Существующие колонки: {existing}")
        print(f"  ❌ Отсутствующие колонки: {missing}")
        
        cur.close()
        conn.close()
        
        return len(missing) == 0
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

if __name__ == "__main__":
    print("🚀 МИГРАЦИЯ POSTGRESQL ДЛЯ СИСТЕМЫ РЕФЕРАЛОВ И РАССЫЛОК")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Режим проверки
        status_ok = check_migration_status()
        sys.exit(0 if status_ok else 1)
    else:
        # Режим миграции
        success = migrate_postgres_columns()
        sys.exit(0 if success else 1)
