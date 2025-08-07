"""
Расширение для PostgresClient для миграции из Google Sheets.
"""

import logging
import datetime
import pytz
from sqlalchemy import select, insert, update
from sqlalchemy.exc import SQLAlchemyError

def user_exists(self, user_id):
    """
    Проверяет существование пользователя в базе данных.
    
    Args:
        user_id (int): Telegram ID пользователя
    
    Returns:
        bool: True если пользователь существует, False иначе
    """
    try:
        with self.engine.connect() as connection:
            query = select(self.users_table).where(self.users_table.c.user_id == user_id)
            result = connection.execute(query).fetchone()
            return result is not None
    except SQLAlchemyError as e:
        logging.error(f"Error checking user existence: {e}")
        return False

def add_user(self, user_id, username=None, first_name=None, phone_number=None, 
             real_name=None, birth_date=None, status='registered', source='direct',
             referrer_id=None, signup_date=None, redeem_date=None):
    """
    Добавляет нового пользователя в базу данных.
    
    Args:
        user_id (int): Telegram ID пользователя
        username (str, optional): Telegram username
        first_name (str, optional): Telegram first name
        phone_number (str, optional): Номер телефона
        real_name (str, optional): Настоящее имя
        birth_date (str, optional): Дата рождения
        status (str, optional): Статус пользователя
        source (str, optional): Источник привлечения
        referrer_id (int, optional): ID пользователя-реферера
        signup_date (datetime, optional): Дата регистрации
        redeem_date (datetime, optional): Дата погашения купона
        
    Returns:
        bool: True если пользователь добавлен успешно, False иначе
    """
    try:
        # Если дата регистрации не указана, используем текущую
        if signup_date is None:
            signup_date = datetime.datetime.now(pytz.UTC)
            
        with self.engine.connect() as connection:
            # Проверяем существование пользователя
            if self.user_exists(user_id):
                logging.info(f"User {user_id} already exists in the database")
                return False
            
            # Формируем данные для вставки
            insert_data = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'status': status,
                'source': source,
                'referrer_id': referrer_id,
                'register_date': signup_date,
                'last_activity': signup_date
            }
            
            # Добавляем дополнительные поля, если они есть в таблице
            for column in self.users_table.columns:
                if column.name == 'phone_number' and phone_number:
                    insert_data['phone_number'] = phone_number
                if column.name == 'real_name' and real_name:
                    insert_data['real_name'] = real_name
                if column.name == 'birth_date' and birth_date:
                    insert_data['birth_date'] = birth_date
                if column.name == 'redeem_date' and redeem_date:
                    insert_data['redeem_date'] = redeem_date
            
            # Выполняем вставку
            query = insert(self.users_table).values(**insert_data)
            connection.execute(query)
            connection.commit()
            
            logging.info(f"User {user_id} successfully added to the database")
            return True
    except SQLAlchemyError as e:
        logging.error(f"Error adding user {user_id}: {e}")
        return False

# Добавляем методы в класс PostgresClient
def add_migration_methods():
    from db.postgres_client import PostgresClient
    PostgresClient.user_exists = user_exists
    PostgresClient.add_user = add_user
    logging.info("Migration methods added to PostgresClient")
