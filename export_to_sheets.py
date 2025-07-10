# export_to_sheets.py
import sqlite3
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_FILE = "evgenich_data.db"
EXPORT_SHEET_NAME = "Выгрузка Пользователей"

COLUMN_CONFIG = {
    "signup_date": "Дата Регистрации",
    "user_id": "ID Пользователя",
    "first_name": "Имя",
    "username": "Юзернейм в Telegram",
    "status": "Статус Награды",
    "source": "Источник Привлечения",
    "referrer_id": "ID Пригласившего",
    "redeem_date": "Дата Погашения"
}

def do_export() -> Tuple[bool, str]:
    """
    Экспортирует данные из SQLite в Google Sheets.
    Возвращает кортеж (успех: bool, сообщение: str).
    """
    logging.info(f"Начинаю экспорт данных в Google Sheets, лист '{EXPORT_SHEET_NAME}'...")

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY signup_date DESC")
        users = cur.fetchall()
        conn.close()
        if not users:
            msg = "В базе данных нет пользователей для экспорта."
            logging.info(msg)
            return True, msg
        logging.info(f"Получено {len(users)} пользователей из SQLite.")
    except Exception as e:
        msg = f"Не удалось получить данные из SQLite: {e}"
        logging.error(msg)
        return False, msg

    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https.www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = spreadsheet.worksheet(EXPORT_SHEET_NAME)
        logging.info("Успешное подключение к Google Sheets.")
    except gspread.exceptions.WorksheetNotFound:
        msg = f"Ошибка: Лист с именем '{EXPORT_SHEET_NAME}' не найден! Пожалуйста, создайте его."
        logging.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Не удалось подключиться к Google Sheets: {e}"
        logging.error(msg)
        return False, msg

    try:
        worksheet.clear()
        logging.info(f"Лист '{EXPORT_SHEET_NAME}' очищен.")
        
        header_row = list(COLUMN_CONFIG.values())
        column_order_keys = list(COLUMN_CONFIG.keys())
        
        data_to_upload = [header_row]
        for user_row in users:
            ordered_row = []
            for key in column_order_keys:
                value = user_row[key]
                # Форматируем дату, если она есть
                if isinstance(value, str) and 'T' in value:
                     try:
                         value = datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S')
                     except:
                         pass
                ordered_row.append(value)
            data_to_upload.append(ordered_row)

        worksheet.update(data_to_upload, 'A1')
        msg = f"УСПЕХ! Данные ({len(data_to_upload)} строк) успешно выгружены."
        logging.info(msg)
        return True, msg
    except Exception as e:
        msg = f"Ошибка при выгрузке данных в Google Sheets: {e}"
        logging.error(msg)
        return False, msg

if __name__ == '__main__':
    # Этот блок будет выполняться, только если запустить файл напрямую
    # python export_to_sheets.py
    success, message = do_export()
    print(message)
