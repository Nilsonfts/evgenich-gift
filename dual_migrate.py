#!/usr/bin/env python3
# coding: utf-8

"""
Скрипт для двойной миграции данных из Google Sheets в SQLite и PostgreSQL.
Данные сохраняются параллельно в обе базы данных.
"""

import os
import sys
import json
import logging
import datetime
import argparse
import sqlite3
import pytz
import gspread
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.sql import select, insert
from sqlalchemy.exc import SQLAlchemyError
from google.oauth2.service_account import Credentials
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

class SimplePostgresClient:
    """Упрощенный класс для работы с PostgreSQL."""
    
    def __init__(self, db_url, recreate_table=False):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        
        # Определяем таблицу пользователей
        self.users_table = Table(
            'users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', sa.BigInteger, nullable=False, unique=True),
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
            Column('referrer_id', sa.BigInteger),
            Column('brought_by_staff_id', Integer),
            Column('profile_completed', Boolean, default=False),
            Column('ai_concept', String(20), default='evgenich'),
        )
        
        # Проверяем и создаем таблицу, если её нет, или пересоздаем если указан флаг
        try:
            if recreate_table:
                # Удаляем таблицу, если она существует
                self.users_table.drop(self.engine, checkfirst=True)
                logging.info("Таблица users в PostgreSQL была удалена для пересоздания")
            
            self.users_table.create(self.engine, checkfirst=True)
            logging.info("Таблица users в PostgreSQL создана или уже существует")
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при создании/пересоздании таблицы users в PostgreSQL: {e}")
            raise
    
    def user_exists(self, user_id):
        """Проверяет существование пользователя в базе данных."""
        try:
            with self.engine.connect() as connection:
                query = select(self.users_table).where(self.users_table.c.user_id == user_id)
                result = connection.execute(query).fetchone()
                return result is not None
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при проверке существования пользователя в PostgreSQL: {e}")
            return False
    
    def add_user(self, user_data):
        """Добавляет пользователя в базу данных."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(insert(self.users_table).values(**user_data))
                connection.commit()
                return True
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при добавлении пользователя в PostgreSQL: {e}")
            return False

class SQLiteClient:
    """Класс для работы с SQLite."""
    
    def __init__(self, db_path, recreate_table=False):
        self.db_path = db_path
        
        # Проверяем наличие таблицы users
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        if recreate_table:
            self.cursor.execute("DROP TABLE IF EXISTS users")
            logging.info("Таблица users в SQLite была удалена для пересоздания")
        
        # Создаем таблицу users, если она не существует
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            status TEXT DEFAULT 'registered',
            phone_number TEXT,
            real_name TEXT,
            birth_date TEXT,
            register_date TEXT,
            last_activity TEXT,
            redeem_date TEXT,
            source TEXT,
            referrer_id INTEGER,
            brought_by_staff_id INTEGER,
            profile_completed INTEGER DEFAULT 0,
            ai_concept TEXT DEFAULT 'evgenich'
        )
        ''')
        self.conn.commit()
        logging.info("Таблица users в SQLite создана или уже существует")
    
    def user_exists(self, user_id):
        """Проверяет существование пользователя в базе данных."""
        try:
            self.cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result is not None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке существования пользователя в SQLite: {e}")
            return False
    
    def add_user(self, user_data):
        """Добавляет пользователя в базу данных."""
        try:
            # Преобразуем даты в строки для SQLite
            sqlite_data = user_data.copy()
            for key in ['register_date', 'last_activity', 'redeem_date']:
                if key in sqlite_data and sqlite_data[key] is not None:
                    sqlite_data[key] = sqlite_data[key].isoformat()
            
            # Создаем запрос и параметры
            columns = ', '.join(sqlite_data.keys())
            placeholders = ', '.join(['?'] * len(sqlite_data))
            values = list(sqlite_data.values())
            
            query = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении пользователя в SQLite: {e}")
            return False
    
    def close(self):
        """Закрывает соединение с базой данных."""
        self.cursor.close()
        self.conn.close()

def get_sheets_data(creds_file, sheet_key, sheet_name):
    """Получает данные из Google Sheets."""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        credentials = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(credentials)
        
        spreadsheet = client.open_by_key(sheet_key)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        
        # Пропускаем заголовок и возвращаем только данные
        return data[1:] if len(data) > 1 else []
    except Exception as e:
        logging.error(f"Ошибка при получении данных из Google Sheets: {e}")
        return []

def migrate_data(pg_db_url, sqlite_db_path, creds_file, sheet_key, sheet_name="Выгрузка Пользователей", recreate_tables=False):
    """Мигрирует данные из Google Sheets в PostgreSQL и SQLite."""
    pg_client = SimplePostgresClient(pg_db_url, recreate_tables)
    sqlite_client = SQLiteClient(sqlite_db_path, recreate_tables)
    
    # Получаем данные из Google Sheets
    sheets_data = get_sheets_data(creds_file, sheet_key, sheet_name)
    if not sheets_data:
        logging.warning("Нет данных для миграции")
        sqlite_client.close()
        return
    
    logging.info(f"Получено {len(sheets_data)} записей из Google Sheets")
    
    # Счетчики для статистики
    added_count_pg = 0
    skipped_count_pg = 0
    added_count_sqlite = 0
    skipped_count_sqlite = 0
    error_count = 0
    
    # UTC временная зона
    utc = pytz.UTC
    
    # Проходим по всем строкам данных
    for row in sheets_data:
        try:
            # Структура данных в таблице:
            # 0: signup_date, 1: user_id, 2: first_name, 3: username, 
            # 4: phone_number, 5: real_name, 6: birth_date, 
            # 7: status, 8: source, 9: referrer_id, 10: redeem_date
            
            if len(row) < 11:  # Проверка, что у нас есть все необходимые данные
                logging.warning(f"Недостаточно данных в строке: {row}")
                skipped_count_pg += 1
                skipped_count_sqlite += 1
                continue
                
            # Получаем данные из строки
            signup_date_str = row[0]
            user_id_str = row[1]
            first_name = row[2]
            username = row[3] if row[3] else None
            phone_number = row[4] if row[4] else None
            real_name = row[5] if row[5] else None
            birth_date = row[6] if row[6] else None
            status = row[7] if row[7] else "registered"
            source = row[8] if row[8] else None
            referrer_id_str = row[9] if row[9] else None
            redeem_date_str = row[10] if len(row) > 10 and row[10] else None
            
            # Преобразуем строки в соответствующие типы
            try:
                user_id = int(user_id_str)
            except ValueError:
                logging.warning(f"Некорректный user_id: {user_id_str}")
                skipped_count_pg += 1
                skipped_count_sqlite += 1
                continue
                
            try:
                referrer_id = int(referrer_id_str) if referrer_id_str else None
            except ValueError:
                referrer_id = None
                
            # Преобразуем строки дат в объекты datetime
            try:
                # Парсим дату в формате DD.MM.YYYY HH:MM:SS, если возможно
                if signup_date_str:
                    if ' ' in signup_date_str:
                        signup_date = datetime.datetime.strptime(signup_date_str, "%d.%m.%Y %H:%M:%S").replace(tzinfo=utc)
                    else:
                        signup_date = datetime.datetime.strptime(signup_date_str, "%d.%m.%Y").replace(tzinfo=utc)
                else:
                    signup_date = datetime.datetime.now(utc)
            except ValueError:
                # Если не удалось, используем текущую дату
                signup_date = datetime.datetime.now(utc)
                
            try:
                # Парсим дату в формате DD.MM.YYYY HH:MM:SS, если возможно
                if redeem_date_str:
                    if ' ' in redeem_date_str:
                        redeem_date = datetime.datetime.strptime(redeem_date_str, "%d.%m.%Y %H:%M:%S").replace(tzinfo=utc)
                    else:
                        redeem_date = datetime.datetime.strptime(redeem_date_str, "%d.%m.%Y").replace(tzinfo=utc)
                else:
                    redeem_date = None
            except ValueError:
                redeem_date = None
                
            # Создаем объект с данными пользователя для добавления в базу данных
            user_data = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'status': status,
                'phone_number': phone_number,
                'real_name': real_name,
                'birth_date': birth_date,
                'register_date': signup_date,
                'last_activity': signup_date,
                'redeem_date': redeem_date,
                'source': source,
                'referrer_id': referrer_id,
                'profile_completed': False,
                'ai_concept': 'evgenich'
            }
            
            # Проверяем, существует ли пользователь в PostgreSQL
            if pg_client.user_exists(user_id):
                logging.info(f"Пользователь {user_id} уже существует в PostgreSQL БД, пропускаем")
                skipped_count_pg += 1
            else:
                # Добавляем пользователя в PostgreSQL
                success = pg_client.add_user(user_data)
                if success:
                    logging.info(f"Пользователь {user_id} успешно добавлен в PostgreSQL")
                    added_count_pg += 1
                else:
                    logging.warning(f"Не удалось добавить пользователя {user_id} в PostgreSQL")
                    skipped_count_pg += 1
            
            # Проверяем, существует ли пользователь в SQLite
            if sqlite_client.user_exists(user_id):
                logging.info(f"Пользователь {user_id} уже существует в SQLite БД, пропускаем")
                skipped_count_sqlite += 1
            else:
                # Добавляем пользователя в SQLite
                success = sqlite_client.add_user(user_data)
                if success:
                    logging.info(f"Пользователь {user_id} успешно добавлен в SQLite")
                    added_count_sqlite += 1
                else:
                    logging.warning(f"Не удалось добавить пользователя {user_id} в SQLite")
                    skipped_count_sqlite += 1
                
        except Exception as e:
            logging.error(f"Ошибка при обработке строки {row}: {e}")
            error_count += 1
    
    # Итоги миграции
    logging.info(f"Миграция в PostgreSQL завершена. Добавлено: {added_count_pg}, Пропущено: {skipped_count_pg}")
    logging.info(f"Миграция в SQLite завершена. Добавлено: {added_count_sqlite}, Пропущено: {skipped_count_sqlite}")
    logging.info(f"Общее количество ошибок: {error_count}")
    
    # Закрываем соединение с SQLite
    sqlite_client.close()

def main():
    parser = argparse.ArgumentParser(description="Двойная миграция данных из Google Sheets в PostgreSQL и SQLite")
    parser.add_argument('--pg-db-url', required=True, help='URL для подключения к PostgreSQL')
    parser.add_argument('--sqlite-db-path', required=True, help='Путь к файлу SQLite базы данных')
    parser.add_argument('--creds-file', required=True, help='Путь к JSON-файлу с учетными данными Google')
    parser.add_argument('--sheet-key', required=True, help='Идентификатор таблицы Google Sheets')
    parser.add_argument('--sheet-name', default="Выгрузка Пользователей", help='Название листа в таблице')
    parser.add_argument('--recreate-tables', action='store_true', help='Пересоздать таблицы перед миграцией')
    
    args = parser.parse_args()
    
    logging.info("Начинаем двойную миграцию данных из Google Sheets в PostgreSQL и SQLite")
    migrate_data(
        args.pg_db_url, 
        args.sqlite_db_path, 
        args.creds_file, 
        args.sheet_key, 
        args.sheet_name,
        args.recreate_tables
    )
    logging.info("Двойная миграция завершена")

if __name__ == "__main__":
    main()
