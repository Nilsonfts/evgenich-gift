import logging
import json
import datetime
from typing import Optional, Tuple, List, Dict
import pytz
from collections import Counter

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None

from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# Column numbers
COL_USER_ID = 2
COL_STATUS = 5
COL_REFERRED_BY = 6
COL_FRIEND_BONUS = 7
COL_SOURCE = 8
COL_REDEEM_DATE = 9

def get_sheet() -> Optional[gspread.Worksheet]:
    if not gspread:
        logging.error("The gspread library is not installed.")
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
        logging.error(f"Error connecting to Google Sheets: {e}")
        return None

def find_user_by_id(user_id: int) -> Optional[gspread.Cell]:
    try:
        worksheet = get_sheet()
        if not worksheet: return None
        return worksheet.find(str(user_id), in_column=COL_USER_ID)
    except gspread.exceptions.CellNotFound:
        return None
    except Exception as e:
        logging.error(f"Error finding user {user_id} in Google Sheets: {e}")
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
    """Adds a new user with the 'registered' status."""
    try:
        if find_user_by_id(user_id):
            logging.info(f"Attempted to add existing user {user_id}. Operation skipped.")
            return

        worksheet = get_sheet()
        if not worksheet: return
        current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if not worksheet.get_all_values():
             headers = ['Дата подписки (UTC)', 'ID Пользователя', 'Username', 'Имя', 'Статус награды', 'Пригласил (ID)', 'Бонус за друга', 'Источник', 'Дата погашения (UTC)']
             worksheet.insert_row(headers, 1)
             worksheet.format('A1:I1', {'textFormat': {'bold': True}})
        
        row_to_add = [current_time_utc, user_id, username, first_name, 'registered', referrer_id if referrer_id else '', '', source, '']
        worksheet.append_row(row_to_add)
        logging.info(f"User {user_id} added with status 'registered'. Source: {source}, Referred by: {referrer_id}")
    except Exception as e:
        logging.error(f"Could not add user {user_id} to Google Sheet: {e}")

def update_status(user_id: int, new_status: str) -> bool:
    """Updates the user's reward status and redemption date if needed."""
    try:
        cell = find_user_by_id(user_id)
        if not cell: return False
        worksheet = get_sheet()
        if not worksheet: return False
        
        worksheet.update_cell(cell.row, COL_STATUS, new_status)
        
        if new_status == 'redeemed':
             current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
             worksheet.update_cell(cell.row, COL_REDEEM_DATE, current_time_utc)
        
        logging.info(f"User {user_id} status updated to {new_status}")
        return True
    except Exception as e:
        logging.error(f"Could not update status for user {user_id}: {e}")
        return False

def delete_user(user_id: int) -> Tuple[bool, str]:
    """Deletes a user and verifies the deletion."""
    try:
        worksheet = get_sheet()
        if not worksheet: return False, "Could not access the sheet."
        all_records = worksheet.get_all_records()
        row_to_delete = -1
        for index, record in enumerate(all_records):
            if str(record.get('ID Пользователя')) == str(user_id):
                row_to_delete = index + 2
                break
        if row_to_delete != -1:
            worksheet.delete_rows(row_to_delete)
            cell_after_delete = find_user_by_id(user_id)
            if cell_after_delete is None:
                msg = f"User {user_id} successfully deleted. Verification confirmed."
                logging.info(msg)
                return True, msg
            else:
                msg = "Deletion command sent, but user is still in the database. Check 'Editor' permissions for the service account."
                logging.error(msg)
                return False, msg
        else:
            msg = f"User {user_id} not found in the sheet for deletion."
            logging.info(msg)
            return False, msg
    except Exception as e:
        error_msg = f"Error deleting user {user_id}: {e}"
        logging.error(error_msg)
        return False, str(e)

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
        logging.error(f"Error counting referrals for {referrer_id}: {e}")
        return 0

def mark_referral_bonus_claimed(referred_user_id: int):
    cell = find_user_by_id(referred_user_id)
    if not cell: return
    worksheet = get_sheet()
    if not worksheet: return
    worksheet.update_cell(cell.row, COL_FRIEND_BONUS, 'claimed')

def get_report_data_for_period(start_time: datetime.datetime, end_time: datetime.datetime) -> tuple:
    try:
        worksheet = get_sheet()
        if not worksheet: return 0, 0, [], {}, 0
        all_records = worksheet.get_all_records()
        issued_count, redeemed_count, redeemed_users, sources, total_redeem_time_seconds = 0, 0, [], {}, 0
        for record in all_records:
            try:
                signup_time_naive = datetime.datetime.strptime(record['Дата подписки (UTC)'], "%Y-%m-%d %H:%M:%S")
                signup_time_utc = pytz.utc.localize(signup_time_naive)
                if start_time <= signup_time_utc < end_time:
                    if record.get('Статус награды') in ['issued', 'redeemed']:
                        issued_count += 1
                    source = record.get('Источник', 'unknown')
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
        logging.error(f"Error gathering data for report: {e}")
        return 0, 0, [], {}, 0

def get_stats_by_source() -> Dict[str, Dict[str, int]]:
    try:
        worksheet = get_sheet()
        if not worksheet: return {}
        all_records = worksheet.get_all_records()
        source_stats = {}
        for record in all_records:
            source = record.get('Источник', 'unknown')
            if not source: source = 'unknown'
            if source not in source_stats:
                source_stats[source] = {'issued': 0, 'redeemed': 0}
            if record.get('Статус награды') in ['issued', 'redeemed']:
                 source_stats[source]['issued'] += 1
            if record.get('Статус награды') == 'redeemed':
                source_stats[source]['redeemed'] += 1
        return source_stats
    except Exception as e:
        logging.error(f"Error gathering stats by source: {e}")
        return {}

def get_weekly_cohort_data() -> List[Dict]:
    try:
        worksheet = get_sheet()
        if not worksheet: return []
        all_records = worksheet.get_all_records()
        tz_moscow = pytz.timezone('Europe/Moscow')
        now_moscow = datetime.datetime.now(tz_moscow)
        cohorts = {}
        for i in range(4):
            end_of_week = (now_moscow - datetime.timedelta(weeks=i)).replace(hour=23, minute=59, second=59)
            start_of_week = (end_of_week - datetime.timedelta(days=6)).replace(hour=0, minute=0, second=0)
            week_key = f"{start_of_week.strftime('%d.%m')}-{end_of_week.strftime('%d.%m.%Y')}"
            cohorts[week_key] = {'start': start_of_week, 'end': end_of_week, 'issued': 0, 'redeemed': 0}
        for record in all_records:
            try:
                signup_time_naive = datetime.datetime.strptime(record['Дата подписки (UTC)'], "%Y-%m-%d %H:%M:%S")
                signup_time_utc = pytz.utc.localize(signup_time_naive)
                for week_key, dates in cohorts.items():
                    if dates['start'] <= signup_time_utc <= dates['end']:
                        if record.get('Статус награды') in ['issued', 'redeemed']:
                            cohorts[week_key]['issued'] += 1
                        if record.get('Статус награды') == 'redeemed':
                            cohorts[week_key]['redeemed'] += 1
                        break
            except (ValueError, TypeError, KeyError):
                continue
        return [{'week': key, **value} for key, value in cohorts.items()]
    except Exception as e:
        logging.error(f"Error gathering cohort data: {e}")
        return []

def get_top_referrers(limit: int = 5) -> List[Tuple[str, int]]:
    try:
        worksheet = get_sheet()
        if not worksheet: return []
        all_records = worksheet.get_all_records()
        successful_referrals = []
        for record in all_records:
            if record.get('Статус награды') == 'redeemed' and record.get('Пригласил (ID)'):
                successful_referrals.append(str(record['Пригласил (ID)']))
        if not successful_referrals:
            return []
        referrer_counts = Counter(successful_referrals)
        top_referrers = []
        user_map = {str(rec.get('ID Пользователя')): f"@{rec['Username']}" if rec.get('Username') else rec.get('Имя', 'Anonymous') for rec in all_records if rec.get('ID Пользователя')}
        for user_id, count in referrer_counts.most_common(limit):
            name = user_map.get(user_id, f"ID: {user_id}")
            top_referrers.append((name, count))
        return top_referrers
    except Exception as e:
        logging.error(f"Error getting top referrers: {e}")
        return []

def log_conversation_turn(user_id: int, role: str, text: str):
    """Logs one turn of a conversation (from user or bot) to the journal."""
    try:
        # Access the 'conversation_history' sheet
        worksheet = get_sheet().spreadsheet.worksheet('conversation_history')
        if not worksheet:
            logging.error("Sheet 'conversation_history' not found in the spreadsheet!")
            return
        
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([user_id, timestamp, role, text])
    except Exception as e:
        logging.error(f"Error writing to conversation log for user_id {user_id}: {e}")

def get_conversation_history(user_id: int, limit: int = 10) -> list:
    """Retrieves the last 'limit' messages from a user's conversation."""
    history = []
    try:
        worksheet = get_sheet().spreadsheet.worksheet('conversation_history')
        if not worksheet:
            logging.error("Sheet 'conversation_history' not found in the spreadsheet!")
            return history
            
        all_records = worksheet.get_all_records()
        user_records = [rec for rec in all_records if str(rec.get('user_id')) == str(user_id)]
        
        # Get the last 'limit' messages
        for record in user_records[-limit:]:
            history.append({"role": record.get('role'), "content": record.get('text')})
            
        return history
    except Exception as e:
        logging.error(f"Error getting conversation history for user_id {user_id}: {e}")
        return history

# === NEW FUNCTION FOR DAILY SPECIALS AND STOP LIST ===
def get_daily_updates() -> dict:
    """Reads operational data from the 'daily_updates' sheet."""
    updates = {'special': 'нет', 'stop-list': 'ничего'}
    try:
        worksheet = get_sheet().spreadsheet.worksheet('daily_updates')
        if not worksheet:
            logging.warning("Sheet 'daily_updates' not found. AI will not have daily specials info.")
            return updates
            
        records = worksheet.get_all_records()
        specials = [rec['item_name'] for rec in records if rec.get('status') == 'special']
        stop_list = [rec['item_name'] for rec in records if rec.get('status') == 'stop-list']
        
        if specials:
            updates['special'] = ", ".join(specials)
        if stop_list:
            updates['stop-list'] = ", ".join(stop_list)
            
        return updates
    except gspread.exceptions.WorksheetNotFound:
        logging.warning("Sheet 'daily_updates' not found. AI will not have daily specials info.")
        return updates
    except Exception as e:
        logging.error(f"Error reading the 'daily_updates' sheet: {e}")
        return updates
