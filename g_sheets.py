# g_sheets.py
import logging
import json
import datetime
from typing import Optional

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None

from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

def get_sheet() -> Optional[gspread.Worksheet]:
    """Аутентифицируется и возвращает рабочий лист Google Таблицы."""
    if not gspread:
        logging.error("Библиотека gspread не установлена. Установите: pip install gspread")
        return None
    try:
        # Загружаем креды из JSON-строки
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        return spreadsheet.sheet1
    except Exception as e:
        logging.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def add_subscription_to_sheet(user_id: int, username: str, first_name: str):
    """Добавляет информацию о новом подписчике в таблицу."""
    try:
        worksheet = get_sheet()
        if not worksheet:
            logging.error("Не удалось получить доступ к листу для записи данных.")
            return

        # Проверяем, есть ли заголовок
        if worksheet.acell('A1').value != 'Дата подписки':
            worksheet.append_row(['Дата подписки', 'ID Пользователя', 'Username', 'Имя'])
            worksheet.format('A1:D1', {'textFormat': {'bold': True}})

        # Добавляем новую строку
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_to_add = [current_time, user_id, username, first_name]
        worksheet.append_row(row_to_add)
        logging.info(f"Пользователь {user_id} (@{username}) успешно добавлен в Google Таблицу.")

    except Exception as e:
        logging.error(f"Не удалось добавить пользователя {user_id} в Google Таблицу: {e}")
