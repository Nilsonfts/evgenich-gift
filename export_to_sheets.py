# export_to_sheets.py
import sqlite3
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Настройки ---
DB_FILE = "evgenich_data.db"
EXPORT_SHEET_NAME = "Выгрузка Пользователей" 

# --- УЛУЧШЕНИЕ: Задаем порядок и русские названия столбцов ---
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

def export_data():
    """Экспортирует данные из SQLite в Google Sheets с заданным порядком столбцов и русскими заголовками."""
    logging.info(f"Начинаю экспорт данных в Google Sheets, лист '{EXPORT_SHEET_NAME}'...")

    # 1. Получаем данные из SQLite
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Запрос остается тем же
        cur.execute("SELECT * FROM users ORDER BY signup_date DESC")
        users = cur.fetchall()
        conn.close()
        if not users:
            logging.info("В базе данных нет пользователей для экспорта.")
            return
        logging.info(f"Получено {len(users)} пользователей из SQLite.")
    except Exception as e:
        logging.error(f"Не удалось получить данные из SQLite: {e}")
        return

    # 2. Подключаемся к Google Sheets
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
        logging.error(f"Ошибка: Лист с именем '{EXPORT_SHEET_NAME}' не найден! Пожалуйста, создайте его.")
        return
    except Exception as e:
        logging.error(f"Не удалось подключиться к Google Sheets: {e}")
        return

    # 3. Очищаем лист и заливаем данные в НУЖНОМ ПОРЯДКЕ
    try:
        worksheet.clear()
        logging.info(f"Лист '{EXPORT_SHEET_NAME}' очищен.")
        
        # --- НОВАЯ ЛОГИКА ФОРМИРОВАНИЯ ТАБЛИЦЫ ---
        
        # 1. Создаем русскую строку заголовков в нужном нам порядке
        header_row = list(COLUMN_CONFIG.values())
        
        # 2. Получаем английские названия колонок в том же порядке
        column_order_keys = list(COLUMN_CONFIG.keys())
        
        # 3. Собираем данные для выгрузки
        data_to_upload = [header_row] # Начинаем с заголовков
        for user_row in users:
            # Для каждой строки пользователя собираем значения в заданном порядке
            ordered_row = [user_row[key] for key in column_order_keys]
            data_to_upload.append(ordered_row)

        worksheet.update(data_to_upload, 'A1')
        logging.info(f"УСПЕХ! Данные ({len(data_to_upload)} строк) успешно выгружены в Google Sheets.")
    except Exception as e:
        logging.error(f"Ошибка при выгрузке данных в Google Sheets: {e}")

if __name__ == '__main__':
    export_data()
