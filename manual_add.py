import database
import logging
import random
import datetime
import pytz

# Настройка, чтобы видеть, что происходит
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def add_lost_users():
    """
    Добавляет 15 условных пользователей, чтобы восстановить счетчик.
    """
    logging.info("Инициализация базы данных для добавления записей...")
    # Убедимся, что таблицы созданы, как это делает main.py
    database.init_db()
    
    # Указываем, сколько записей нужно восстановить
    users_to_add = 15
    source = 'QR на баре' # Источник, как вы и упомянули

    logging.info(f"Начинаю добавление {users_to_add} условных пользователей из источника '{source}'...")

    for i in range(users_to_add):
        # Генерируем случайный ID, чтобы они не пересекались.
        # Берем отрицательные числа, чтобы точно не совпасть с реальными ID.
        user_id = -random.randint(10000, 99999) 
        username = f"восстановлен_{i+1}"
        first_name = "Пользователь"
        
        # Добавляем пользователя
        database.add_new_user(user_id, username, first_name, source, referrer_id=None)
        
        # Сразу же меняем его статус на "выдано" (issued)
        # Это именно тот статус, который учитывается в отчете как "выданный купон"
        database.update_status(user_id, 'issued')

    logging.info(f"Успешно добавлено {users_to_add} записей. Счетчик восстановлен.")

if __name__ == '__main__':
    add_lost_users()
