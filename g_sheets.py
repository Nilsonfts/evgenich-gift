import logging
import json
import datetime
from typing import Optional, Tuple, List
import pytz

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None

from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

COL_USER_ID = 2
COL_STATUS = 5
COL_USERNAME = 3

def get_sheet() -> Optional[gspread.Worksheet]:
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
    try:
        worksheet = get_sheet()
        if not worksheet: return None
        return worksheet.find(str(user_id), in_column=COL_USER_ID)
    except gspread.exceptions.CellNotFound:
        return None
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя {user_id} в Google Sheets: {e}")
        return None

def get_reward_status(user_id: int) -> str:
    cell = find_user_by_id(user_id)
    if not cell:
        return 'not_found'
    worksheet = get_sheet()
    if not worksheet: return 'not_found'
    status = worksheet.cell(cell.row, COL_STATUS).value
    return status or 'not_found'

def add_new_user(user_id: int, username: str, first_name: str):
    try:
        worksheet = get_sheet()
        if not worksheet: return
        current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if not worksheet.get_all_values():
             headers = ['Дата подписки (UTC)', 'ID Пользователя', 'Username', 'Имя', 'Статус награды']
             worksheet.insert_row(headers, 1)
             worksheet.format('A1:E1', {'textFormat': {'bold': True}})
        row_to_add = [current_time_utc, user_id, username, first_name, 'issued']
        worksheet.append_row(row_to_add)
        logging.info(f"Пользователь {user_id} (@{username}) успешно добавлен в Google Таблицу.")
    except Exception as e:
        logging.error(f"Не удалось добавить пользователя {user_id} в Google Таблицу: {e}")

def redeem_reward(user_id: int) -> bool:
    cell = find_user_by_id(user_id)
    if not cell: return False
    worksheet = get_sheet()
    if not worksheet: return False
    current_status = worksheet.cell(cell.row, COL_STATUS).value
    if current_status == 'issued':
        worksheet.update_cell(cell.row, COL_STATUS, 'redeemed')
        return True
    return False

def get_report_data_for_period(start_time: datetime.datetime, end_time: datetime.datetime) -> Tuple[int, int, List[str]]:
    """Собирает данные за период: выдано, погашено, список username'ов погасивших."""
    try:
        worksheet = get_sheet()
        if not worksheet: return 0, 0, []
        all_records = worksheet.get_all_records()
        
        issued_count = 0
        redeemed_count = 0
        redeemed_users = []

        for record in all_records:
            try:
                record_time_naive = datetime.datetime.strptime(record['Дата подписки (UTC)'], "%Y-%m-%d %H:%M:%S")
                record_time_utc = pytz.utc.localize(record_time_naive)
                if start_time <= record_time_utc < end_time:
                    issued_count += 1
                    if record['Статус награды'] == 'redeemed':
                        redeemed_count += 1
                        username = record.get('Username')
                        if username and username != "N/A":
                            redeemed_users.append(f"@{username}")
                        else:
                            # Если нет юзернейма, можно использовать имя или ID
                            redeemed_users.append(record.get('Имя', str(record.get('ID Пользователя'))))

            except (ValueError, TypeError, KeyError):
                continue
        return issued_count, redeemed_count, redeemed_users
    except Exception as e:
        logging.error(f"Ошибка при сборе данных для отчета: {e}")
        return 0, 0, []
