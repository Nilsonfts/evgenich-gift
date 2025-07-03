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

# Номера колонок для удобства
COL_USER_ID = 2
COL_STATUS = 5

def get_sheet() -> Optional[gspread.Worksheet]:
    """Аутентифицируется и возвращает рабочий лист Google Таблицы."""
    if not gspread:
        logging.error("Библиотека gspread не установлена.")
        return None
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        return spreadsheet.sheet1
    except Exception as e:
        logging.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def find_user_by_id(user_id: int) -> Optional[gspread.Cell]:
    """Находит пользователя в таблице по ID и возвращает ячейку."""
    try:
        worksheet = get_sheet()
        if not worksheet: return None
        # ИЗМЕНЕНИЕ БЫЛО ЗДЕСЬ (в gspread.Cell)
        return worksheet.find(str(user_id), in_column=COL_USER_ID)
    except gspread.exceptions.CellNotFound:
        return None
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя {user_id} в Google Sheets: {e}")
        return None

def get_reward_status(user_id: int) -> str:
    """Проверяет статус награды пользователя в таблице."""
    cell = find_user_by_id(user_id)
    if not cell:
        return 'not_found'
    
    worksheet = get_sheet()
    if not worksheet: return 'not_found'
    
    status = worksheet.cell(cell.row, COL_STATUS).value
    return status or 'not_found'

def add_new_user(user_id: int, username: str, first_name: str):
    """Добавляет нового пользователя в таблицу со статусом 'issued'."""
    try:
        worksheet = get_sheet()
        if not worksheet: return

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Проверяем, есть ли заголовки, если лист пустой
        if not worksheet.get_all_values():
             headers = ['Дата подписки', 'ID Пользователя', 'Username', 'Имя', 'Статус награды']
             worksheet.insert_row(headers, 1)
             worksheet.format('A1:E1', {'textFormat': {'bold': True}})

        row_to_add = [current_time, user_id, username, first_name, 'issued']
        worksheet.append_row(row_to_add)
        logging.info(f"Пользователь {user_id} (@{username}) успешно добавлен в Google Таблицу.")
    except Exception as e:
        logging.error(f"Не удалось добавить пользователя {user_id} в Google Таблицу: {e}")

def redeem_reward(user_id: int) -> bool:
    """Погашает награду в таблице. Возвращает True если успешно, иначе False."""
    cell = find_user_by_id(user_id)
    if not cell:
        return False
        
    worksheet = get_sheet()
    if not worksheet: return False

    current_status = worksheet.cell(cell.row, COL_STATUS).value
    if current_status == 'issued':
        worksheet.update_cell(cell.row, COL_STATUS, 'redeemed')
        return True
    return False
