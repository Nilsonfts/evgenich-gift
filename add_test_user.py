import logging
import psycopg2
import sqlite3
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Параметры подключения
pg_db_url = "postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway"
sqlite_db_path = "local_bot_database.db"

# Текущая дата и время
now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")

# Тестовый пользователь
test_user = {
    "user_id": 9999999999,  # Очень большой ID для теста
    "username": "test_dual_user",
    "first_name": "Тестовый",
    "status": "registered",
    "phone_number": "+79999999999",
    "real_name": "Тест Тестович",
    "birth_date": "2000-01-01",
    "register_date": current_time,
    "last_activity": current_time,
    "redeem_date": None,
    "source": "dual_migration_test",
    "referrer_id": None,
    "brought_by_staff_id": None,
    "profile_completed": False,
    "ai_concept": "evgenich"
}

def add_user_to_postgres():
    try:
        # Подключение к PostgreSQL
        conn = psycopg2.connect(pg_db_url)
        cursor = conn.cursor()
        
        # SQL запрос для добавления пользователя
        insert_query = """
        INSERT INTO users (
            user_id, username, first_name, status, phone_number, real_name, 
            birth_date, register_date, last_activity, redeem_date, source,
            referrer_id, brought_by_staff_id, profile_completed, ai_concept
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (user_id) DO NOTHING;
        """
        
        # Выполнение запроса
        cursor.execute(insert_query, (
            test_user["user_id"],
            test_user["username"],
            test_user["first_name"],
            test_user["status"],
            test_user["phone_number"],
            test_user["real_name"],
            test_user["birth_date"],
            test_user["register_date"],
            test_user["last_activity"],
            test_user["redeem_date"],
            test_user["source"],
            test_user["referrer_id"],
            test_user["brought_by_staff_id"],
            test_user["profile_completed"],
            test_user["ai_concept"]
        ))
        
        # Подтверждение транзакции
        conn.commit()
        logging.info(f"Пользователь {test_user['user_id']} добавлен в PostgreSQL БД")
        
        # Закрытие соединения
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя в PostgreSQL: {e}")
        return False

def add_user_to_sqlite():
    try:
        # Подключение к SQLite
        conn = sqlite3.connect(sqlite_db_path)
        cursor = conn.cursor()
        
        # SQL запрос для добавления пользователя
        insert_query = """
        INSERT OR IGNORE INTO users (
            user_id, username, first_name, status, phone_number, real_name, 
            birth_date, register_date, last_activity, redeem_date, source,
            referrer_id, brought_by_staff_id, profile_completed, ai_concept
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
        """
        
        # Выполнение запроса
        cursor.execute(insert_query, (
            test_user["user_id"],
            test_user["username"],
            test_user["first_name"],
            test_user["status"],
            test_user["phone_number"],
            test_user["real_name"],
            test_user["birth_date"],
            test_user["register_date"],
            test_user["last_activity"],
            test_user["redeem_date"],
            test_user["source"],
            test_user["referrer_id"],
            test_user["brought_by_staff_id"],
            test_user["profile_completed"],
            test_user["ai_concept"]
        ))
        
        # Подтверждение транзакции
        conn.commit()
        logging.info(f"Пользователь {test_user['user_id']} добавлен в SQLite БД")
        
        # Закрытие соединения
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя в SQLite: {e}")
        return False

if __name__ == "__main__":
    logging.info("Добавляем тестового пользователя в обе базы данных")
    pg_result = add_user_to_postgres()
    sqlite_result = add_user_to_sqlite()
    
    if pg_result and sqlite_result:
        logging.info("Пользователь успешно добавлен в обе базы данных")
    else:
        logging.error("Ошибка при добавлении пользователя")
