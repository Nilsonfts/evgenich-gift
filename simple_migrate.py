#!/usr/bin/env python3
# coding: utf-8

"""
Скрипт для миграции данных из Google Sheets в базу PostgreSQL.
Упрощенная версия, которая не требует всех переменных окружения.
"""

import os
import json
import logging
import datetime
import pytz
import gspread
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.sql import select, insert
from sqlalchemy.exc import SQLAlchemyError
from google.oauth2.service_account import Credentials

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Переменные для подключения к базам данных
DATABASE_URL = os.environ.get('DATABASE_URL')
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')
GOOGLE_SHEET_KEY = os.environ.get('GOOGLE_SHEET_KEY')
SHEET_NAME = "Выгрузка Пользователей"

# Проверка обязательных переменных
if not all([DATABASE_URL, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_KEY]):
    logging.error("Не указаны обязательные переменные окружения: DATABASE_URL, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_KEY")
    exit(1)

class SimplePostgresClient:
    """Упрощенный класс для работы с PostgreSQL."""
    
    def __init__(self, db_url):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        
        # Определяем таблицу пользователей
        self.users_table = Table(
            'users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, nullable=False, unique=True),
            Column('username', String(100)),
            Column('first_name', String(100)),
            Column('status', String(20), default='registered'),
            Column('phone_number', String(20)),
            Column('real_name', String(100)),
            Column('birth_date', String(20)),
            Column('register_date', DateTime, default=datetime.datetime.now),
            Column('last_activity', DateTime, default=datetime.datetime.now),
            Column('redeem_date', DateTime),
            Column('source', String(50)),
            Column('referrer_id', Integer),
            Column('brought_by_staff_id', Integer),
            Column('profile_completed', Boolean, default=False),
            Column('ai_concept', String(20), default='evgenich'),
        )
        
        # Проверяем и создаем таблицу, если её нет
        try:
            self.users_table.create(self.engine, checkfirst=True)
            logging.info("Таблица users создана или уже существует")
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при создании таблицы users: {e}")
            raise
    
    def user_exists(self, user_id):
        """Проверяет существование пользователя в базе данных."""
        try:
            with self.engine.connect() as connection:
                query = select(self.users_table).where(self.users_table.c.user_id == user_id)
                result = connection.execute(query).fetchone()
                return result is not None
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при проверке существования пользователя: {e}")
            return False
    
    def add_user(self, user_id, username=None, first_name=None, phone_number=None, 
                real_name=None, birth_date=None, status='registered', source='direct',
                referrer_id=None, signup_date=None, redeem_date=None):
        """Добавляет нового пользователя в базу данных."""
        try:
            # Если дата регистрации не указана, используем текущую
            if signup_date is None:
                signup_date = datetime.datetime.now(pytz.UTC)
                
            with self.engine.connect() as connection:
                # Проверяем существование пользователя
                if self.user_exists(user_id):
                    logging.info(f"Пользователь {user_id} уже существует в базе данных")
                    return False
                
                # Формируем данные для вставки
                insert_data = {
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name,
                    'phone_number': phone_number,
                    'real_name': real_name,
                    'birth_date': birth_date,
                    'status': status,
                    'source': source,
                    'referrer_id': referrer_id,
                    'register_date': signup_date,
                    'last_activity': signup_date,
                    'redeem_date': redeem_date
                }
                
                # Выполняем вставку
                query = insert(self.users_table).values(**insert_data)
                connection.execute(query)
                connection.commit()
                
                logging.info(f"Пользователь {user_id} успешно добавлен в базу данных")
                return True
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
            return False

# Словарь для перевода статусов с русского на английский
def _translate_status_from_russian(status: str) -> str:
    """Переводит статус с русского на английский."""
    status_translations = {
        'Зарегистрирован': 'registered',
        'Купон выдан': 'issued',
        'Купон погашен': 'redeemed',
        'Погашен и отписался': 'redeemed_and_left'
    }
    return status_translations.get(status, 'registered')

def get_sheets_data():
    """Получает данные из Google Sheets."""
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        
        # Получаем все данные
        all_data = worksheet.get_all_values()
        
        # Пропускаем заголовок
        if len(all_data) > 1:
            return all_data[1:]  # Пропускаем первую строку заголовков
        return []
    except Exception as e:
        logging.error(f"Ошибка получения данных из Google Sheets: {e}")
        return []

def migrate_data():
    """Мигрирует данные из Google Sheets в PostgreSQL."""
    pg_client = SimplePostgresClient(DATABASE_URL)
    
    # Получаем данные из Google Sheets
    sheets_data = get_sheets_data()
    if not sheets_data:
        logging.warning("Нет данных для миграции")
        return
    
    logging.info(f"Получено {len(sheets_data)} записей из Google Sheets")
    
    # Счетчики для статистики
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    # Проходим по всем строкам данных
    for row in sheets_data:
        try:
            # Структура данных в таблице:
            # 0: signup_date, 1: user_id, 2: first_name, 3: username, 
            # 4: phone_number, 5: real_name, 6: birth_date, 
            # 7: status, 8: source, 9: referrer_id, 10: redeem_date
            
            if len(row) < 11:  # Проверка, что у нас есть все необходимые данные
                logging.warning(f"Недостаточно данных в строке: {row}")
                skipped_count += 1
                continue
                
            user_id = row[1].strip()
            if not user_id.isdigit():
                logging.warning(f"Некорректный user_id: {user_id}")
                skipped_count += 1
                continue
            
            user_id = int(user_id)
            
            # Проверяем существование пользователя
            if pg_client.user_exists(user_id):
                logging.info(f"Пользователь {user_id} уже существует в БД, пропускаем")
                skipped_count += 1
                continue
                
            # Форматируем данные
            signup_date = None
            try:
                if row[0]:
                    signup_date = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
            except ValueError:
                logging.warning(f"Неверный формат даты регистрации для {user_id}: {row[0]}")
            
            redeem_date = None
            try:
                if row[10]:
                    redeem_date = datetime.datetime.strptime(row[10], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
            except ValueError:
                logging.warning(f"Неверный формат даты погашения для {user_id}: {row[10]}")
            
            username = row[3].strip() if row[3].strip() != "N/A" else None
            first_name = row[2].strip()
            phone_number = row[4].strip() or None
            real_name = row[5].strip() or None
            birth_date = row[6].strip() or None
            status = _translate_status_from_russian(row[7].strip())
            source = row[8].strip() or "direct"
            referrer_id = None
            if row[9].strip() and row[9].strip().isdigit():
                referrer_id = int(row[9].strip())
            
            # Добавляем пользователя в PostgreSQL
            success = pg_client.add_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                phone_number=phone_number,
                real_name=real_name,
                birth_date=birth_date,
                status=status,
                source=source,
                referrer_id=referrer_id,
                signup_date=signup_date,
                redeem_date=redeem_date
            )
            
            if success:
                logging.info(f"Пользователь {user_id} успешно добавлен в PostgreSQL")
                added_count += 1
            else:
                logging.warning(f"Не удалось добавить пользователя {user_id}")
                skipped_count += 1
                
        except Exception as e:
            logging.error(f"Ошибка при обработке строки {row}: {e}")
            error_count += 1
    
    # Итоги миграции
    logging.info(f"Миграция завершена. Добавлено: {added_count}, Пропущено: {skipped_count}, Ошибок: {error_count}")

if __name__ == "__main__":
    logging.info("Начинаем миграцию данных из Google Sheets в PostgreSQL")
    migrate_data()
    logging.info("Миграция завершена")
