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
COL_SOURCE = 8
COL_REDEEM_DATE = 9

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

def add_new_user(user_id: int, username: str, first_name: str, source: str, referrer_id: Optional[int] = None):
    try:
        worksheet = get_sheet()
        if not worksheet: return
        current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if not worksheet.get_all_values():
             headers = ['Дата подписки (UTC)', 'ID Пользователя', 'Username', 'Имя', 'Статус награды', 'Пригласил (ID)', 'Бонус за друга', 'Источник', 'Дата погашения (UTC)']
             worksheet.insert_row(headers, 1)
             worksheet.format('A1:I1', {'textFormat': {'bold': True}})
        
        row_to_add = [current_time_utc, user_id, username, first_name, 'issued', referrer_id if referrer_id else '', '', source, '']
        worksheet.append_row(row_to_add)
        logging.info(f"Пользователь {user_id} добавлен. Источник: {source}, Пригласил: {referrer_id}")
    except Exception as e:
        logging.error(f"Не удалось добавить пользователя {user_id} в Google Таблицу: {e}")

def redeem_reward(user_id: int) -> bool:
    cell = find_user_by_id(user_id)
    if not cell: return False
    worksheet = get_sheet()
    if not worksheet: return False
    
    current_status = worksheet.cell(cell.row, COL_STATUS).value
    if current_status == 'issued':
        current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.update_cell(cell.row, COL_STATUS, 'redeemed')
        worksheet.update_cell(cell.row, COL_REDEEM_DATE, current_time_utc)
        return True
    return False

def get_referrer_id_from_user(user_id: int) -> Optional[int]:
    cell = find_user_by_id(user_id)
    if not cell: return None
    worksheet = get_sheet()
    if not worksheet: return None
    referrer_id_str = worksheet.cell(cell.row, COL_REFERRED_BY).value
    return int(referrer_id_str) if referrer_id_str else None

def count_successful_referrals(referrer_id: int) -> int:
    try:
        worksheet = get_sheet()
        if not worksheet: return 0
        all_referrer_cells = worksheet.findall(str(referrer_id), in_column=COL_REFERRED_BY)
        claimed_count = sum(1 for cell in all_referrer_cells if worksheet.cell(cell.row, COL_FRIEND_BONUS).value == 'claimed')
        return claimed_count
    except Exception as e:
        logging.error(f"Ошибка при подсчете рефералов для {referrer_id}: {e}")
        return 0

def mark_referral_bonus_claimed(referred_user_id: int):
    cell = find_user_by_id(referred_user_id)
    if not cell: return
    worksheet = get_sheet()
    if not worksheet: return
    worksheet.update_cell(cell.row, COL_FRIEND_BONUS, 'claimed')

def get_report_data_for_period(start_time: datetime.datetime, end_time: datetime.datetime) -> Tuple[int, int, List[str], dict]:
    """Собирает данные за период: выдано, погашено, список username'ов и источники."""
    try:
        worksheet = get_sheet()
        if not worksheet: return 0, 0, [], {}
        all_records = worksheet.get_all_records()
        
        issued_count = 0
        redeemed_count = 0
        redeemed_users = []
        sources = {}
        total_redeem_time_seconds = 0

        for record in all_records:
            try:
                signup_time_naive = datetime.datetime.strptime(record['Дата подписки (UTC)'], "%Y-%m-%d %H:%M:%S")
                signup_time_utc = pytz.utc.localize(signup_time_naive)

                if start_time <= signup_time_utc < end_time:
                    issued_count += 1
                    source = record.get('Источник', 'неизвестно')
                    sources[source] = sources.get(source, 0) + 1

                    if record['Статус награды'] == 'redeemed' and record.get('Дата погашения (UTC)'):
                        redeemed_count += 1
                        username = record.get('Username')
                        if username and username != "N/A":
                            redeemed_users.append(f"@{username}")
                        else:
                            redeemed_users.append(record.get('Имя', str(record.get('ID Пользователя'))))
                        
                        redeem_time_naive = datetime.datetime.strptime(record['Дата погашения (UTC)'], "%Y-%m-%d %H:%M:%S")
                        time_diff = redeem_time_naive - signup_time_naive
                        total_redeem_time_seconds += time_diff.total_seconds()

            except (ValueError, TypeError, KeyError):
                continue
        return issued_count, redeemed_count, redeemed_users, sources, total_redeem_time_seconds
    except Exception as e:
        logging.error(f"Ошибка при сборе данных для отчета: {e}")
        return 0, 0, [], {}, 0
