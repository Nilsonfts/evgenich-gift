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

# Номера колонок
COL_USER_ID = 2
COL_STATUS = 5
COL_REFERRED_BY = 6
COL_FRIEND_BONUS = 7

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

def add_new_user(user_id: int, username: str, first_name: str, referrer_id: Optional[int] = None):
    """Добавляет нового пользователя, опционально с ID пригласившего."""
    try:
        worksheet = get_sheet()
        if not worksheet: return
        current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Проверяем, есть ли заголовки, если лист пустой
        if not worksheet.get_all_values():
             headers = ['Дата подписки (UTC)', 'ID Пользователя', 'Username', 'Имя', 'Статус награды', 'Пригласил (ID)', 'Бонус за друга']
             worksheet.insert_row(headers, 1)
             worksheet.format('A1:G1', {'textFormat': {'bold': True}})
        
        row_to_add = [current_time_utc, user_id, username, first_name, 'issued', referrer_id if referrer_id else '', '']
        worksheet.append_row(row_to_add)
        logging.info(f"Пользователь {user_id} добавлен в Google Таблицу. Пригласил: {referrer_id}")
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

def get_referrer_id_from_user(user_id: int) -> Optional[int]:
    """Получает ID пригласившего для указанного пользователя."""
    cell = find_user_by_id(user_id)
    if not cell: return None
    worksheet = get_sheet()
    if not worksheet: return None
    referrer_id_str = worksheet.cell(cell.row, COL_REFERRED_BY).value
    return int(referrer_id_str) if referrer_id_str else None

def count_successful_referrals(referrer_id: int) -> int:
    """Считает, сколько бонусов уже получил пригласивший."""
    try:
        worksheet = get_sheet()
        if not worksheet: return 0
        all_referrer_cells = worksheet.findall(str(referrer_id), in_column=COL_REFERRED_BY)
        
        claimed_count = 0
        for cell in all_referrer_cells:
            bonus_status = worksheet.cell(cell.row, COL_FRIEND_BONUS).value
            if bonus_status == 'claimed':
                claimed_count += 1
        return claimed_count
    except Exception as e:
        logging.error(f"Ошибка при подсчете рефералов для {referrer_id}: {e}")
        return 0

def mark_referral_bonus_claimed(referred_user_id: int):
    """Отмечает, что бонус за этого пользователя был выдан."""
    cell = find_user_by_id(referred_user_id)
    if not cell: return
    worksheet = get_sheet()
    if not worksheet: return
    worksheet.update_cell(cell.row, COL_FRIEND_BONUS, 'claimed')

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
                            redeemed_users.append(record.get('Имя', str(record.get('ID Пользователя'))))
            except (ValueError, TypeError, KeyError):
                continue
        return issued_count, redeemed_count, redeemed_users
    except Exception as e:
        logging.error(f"Ошибка при сборе данных для отчета: {e}")
        return 0, 0, []
