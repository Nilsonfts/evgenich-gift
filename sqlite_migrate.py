#!/usr/bin/env python3
# coding: utf-8

"""
Демонстрационный скрипт для миграции данных из Google Sheets в локальную базу SQLite.
Это демонстрация функциональности, которую затем можно будет использовать с PostgreSQL.
"""

import os
import sys
import json
import logging
import datetime
import argparse
import pytz
import gspread
import sqlite3
from pathlib import Path
from google.oauth2.service_account import Credentials

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

class SimpleSQLiteClient:
    """Упрощенный класс для работы с SQLite."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        """Создает необходимые таблицы, если их нет."""
        cursor = self.conn.cursor()
        cursor.execute('''
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
        logging.info("Таблица users создана или уже существует")
    
    def user_exists(self, user_id):
        """Проверяет существование пользователя в базе данных."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
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
            
            # Форматируем даты как строки для SQLite
            signup_date_str = signup_date.strftime("%Y-%m-%d %H:%M:%S") if signup_date else None
            redeem_date_str = redeem_date.strftime("%Y-%m-%d %H:%M:%S") if redeem_date else None
            
            # Проверяем существование пользователя
            if self.user_exists(user_id):
                logging.info(f"Пользователь {user_id} уже существует в базе данных")
                return False
            
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO users (
                user_id, username, first_name, phone_number, real_name, 
                birth_date, status, source, referrer_id, register_date, last_activity, redeem_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, first_name, phone_number, real_name,
                birth_date, status, source, referrer_id, signup_date_str, signup_date_str, redeem_date_str
            ))
            self.conn.commit()
            
            logging.info(f"Пользователь {user_id} успешно добавлен в базу данных")
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
            return False
    
    def close(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()

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

def get_sheets_data(creds_file, sheet_key, sheet_name="Выгрузка Пользователей"):
    """Получает данные из Google Sheets."""
    try:
        # Проверяем, существует ли файл с учетными данными
        creds_path = Path(creds_file)
        if not creds_path.exists():
            logging.error(f"Файл с учетными данными не найден: {creds_file}")
            return []
            
        # Загружаем учетные данные
        with open(creds_path, 'r') as f:
            creds_dict = json.load(f)
            
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_key)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Получаем все данные
        all_data = worksheet.get_all_values()
        
        # Пропускаем заголовок
        if len(all_data) > 1:
            return all_data[1:]  # Пропускаем первую строку заголовков
        return []
    except Exception as e:
        logging.error(f"Ошибка получения данных из Google Sheets: {e}")
        return []

def migrate_data(db_path, creds_file, sheet_key, sheet_name="Выгрузка Пользователей"):
    """Мигрирует данные из Google Sheets в SQLite."""
    try:
        # Создаем клиент SQLite
        sqlite_client = SimpleSQLiteClient(db_path)
        
        # Получаем данные из Google Sheets
        sheets_data = get_sheets_data(creds_file, sheet_key, sheet_name)
        if not sheets_data:
            logging.warning("Нет данных для миграции")
            sqlite_client.close()
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
                if sqlite_client.user_exists(user_id):
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
                
                # Добавляем пользователя в SQLite
                success = sqlite_client.add_user(
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
                    logging.info(f"Пользователь {user_id} успешно добавлен в SQLite")
                    added_count += 1
                else:
                    logging.warning(f"Не удалось добавить пользователя {user_id}")
                    skipped_count += 1
                    
            except Exception as e:
                logging.error(f"Ошибка при обработке строки {row}: {e}")
                error_count += 1
        
        # Итоги миграции
        logging.info(f"Миграция завершена. Добавлено: {added_count}, Пропущено: {skipped_count}, Ошибок: {error_count}")
        
        # Закрываем соединение
        sqlite_client.close()
        
    except Exception as e:
        logging.error(f"Общая ошибка в процессе миграции: {e}")

def main():
    parser = argparse.ArgumentParser(description="Миграция данных из Google Sheets в SQLite")
    parser.add_argument('--db-path', required=True, help='Путь к файлу SQLite базы данных')
    parser.add_argument('--creds-file', required=True, help='Путь к JSON-файлу с учетными данными Google')
    parser.add_argument('--sheet-key', required=True, help='Идентификатор таблицы Google Sheets')
    parser.add_argument('--sheet-name', default="Выгрузка Пользователей", help='Название листа в таблице')
    
    args = parser.parse_args()
    
    logging.info("Начинаем миграцию данных из Google Sheets в SQLite")
    migrate_data(args.db_path, args.creds_file, args.sheet_key, args.sheet_name)
    logging.info("Миграция завершена")

if __name__ == "__main__":
    main()
