"""
Пример использования DualDatabase для работы с обеими базами данных.
"""
import logging
from dual_database import DualDatabase

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Параметры подключения
PG_DB_URL = "postgresql://postgres:nfEjoLHipQhZXzxrdgmhvpcCeYljqEzv@tramway.proxy.rlwy.net:36580/railway"
SQLITE_DB_PATH = "local_bot_database.db"

def main():
    # Инициализация базы данных с двумя подключениями
    db = DualDatabase(pg_url=PG_DB_URL, sqlite_path=SQLITE_DB_PATH)
    
    # Пример получения данных пользователя
    user_id = 9999999999  # ID тестового пользователя, которого мы добавили ранее
    user_data = db.get_user(user_id)
    
    if user_data:
        print(f"Найден пользователь с ID {user_id}:")
        print(f"Имя пользователя: {user_data.get('username')}")
        print(f"Имя: {user_data.get('first_name')}")
        print(f"Источник: {user_data.get('source')}")
    else:
        print(f"Пользователь с ID {user_id} не найден")
    
    # Пример обновления данных пользователя
    update_data = {
        "real_name": "Тестовый Пользователь Обновленный",
        "source": "dual_database_example"
    }
    
    print(f"\nОбновляем данные пользователя {user_id}...")
    update_result = db.update_user(user_id, update_data)
    
    if update_result:
        print("Данные пользователя успешно обновлены")
    else:
        print("Ошибка при обновлении данных пользователя")
    
    # Получаем обновленные данные пользователя
    updated_user_data = db.get_user(user_id)
    
    if updated_user_data:
        print(f"\nОбновленные данные пользователя с ID {user_id}:")
        print(f"Имя пользователя: {updated_user_data.get('username')}")
        print(f"Имя: {updated_user_data.get('first_name')}")
        print(f"Полное имя: {updated_user_data.get('real_name')}")
        print(f"Источник: {updated_user_data.get('source')}")
    else:
        print(f"Пользователь с ID {user_id} не найден")
    
    # Пример получения списка пользователей
    print("\nПолучаем список последних 5 пользователей:")
    users = db.get_all_users(limit=5)
    
    for i, user in enumerate(users, 1):
        print(f"{i}. ID: {user.get('user_id')}, Имя пользователя: {user.get('username')}")
    
    print(f"\nВсего найдено пользователей: {len(db.get_all_users())}")

if __name__ == "__main__":
    main()
