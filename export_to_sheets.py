# export_to_sheets.py
import sqlite3
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# Настройка логирования, чтобы видеть процесс в консоли
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Настройки ---
# Имя файла вашей локальной базы данных
DB_FILE = "evgenich_data.db" 
# Имя листа в вашей Google-таблице, куда будут выгружаться данные.
# ВАЖНО: Убедитесь, что такой лист существует в вашей таблице!
EXPORT_SHEET_NAME = "Users_Export" 

def export_data():
    """Экспортирует все данные из таблицы 'users' в SQLite в Google Sheets."""
    logging.info(f"Начинаю экспорт данных в Google Sheets, лист '{EXPORT_SHEET_NAME}'...")

    # 1. Получаем данные из локальной базы SQLite
    try:
        # Подключаемся к файлу базы данных
        conn = sqlite3.connect(DB_FILE)
        # Это позволит обращаться к колонкам по имени, как в словаре
        conn.row_factory = sqlite3.Row 
        cur = conn.cursor()
        # Выполняем SQL-запрос, чтобы забрать всех пользователей
        cur.execute("SELECT * FROM users ORDER BY signup_date DESC")
        users = cur.fetchall()
        conn.close()
        
        if not users:
            logging.info("В базе данных нет пользователей для экспорта. Завершаю работу.")
            return
            
        logging.info(f"Получено {len(users)} пользователей из SQLite.")
    except Exception as e:
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить данные из SQLite. Проверьте, что файл '{DB_FILE}' существует. Ошибка: {e}")
        return

    # 2. Подключаемся к Google Sheets, используя ключи из config.py
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        # Пытаемся найти лист с нужным именем
        worksheet = spreadsheet.worksheet(EXPORT_SHEET_NAME)
        logging.info("Успешное подключение к Google Sheets.")
    except gspread.exceptions.WorksheetNotFound:
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: Лист с именем '{EXPORT_SHEET_NAME}' не найден в вашей Google-таблице! Пожалуйста, создайте его и попробуйте снова.")
        return
    except Exception as e:
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось подключиться к Google Sheets. Проверьте ваши ключи в .env файле. Ошибка: {e}")
        return

    # 3. Очищаем лист и заливаем свежие данные
    try:
        worksheet.clear()
        logging.info(f"Лист '{EXPORT_SHEET_NAME}' успешно очищен.")
        
        # Готовим данные к отправке: сначала строка с заголовками, потом все строки с данными
        header = list(users[0].keys())
        data_to_upload = [header] + [list(row) for row in users]

        # Одной командой выгружаем все данные
        worksheet.update(data_to_upload, 'A1')
        logging.info(f"УСПЕХ! Данные ({len(data_to_upload)} строк) успешно выгружены в Google Sheets.")
    except Exception as e:
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: Ошибка при выгрузке данных в Google Sheets. {e}")

if __name__ == '__main__':
    # Эта часть кода позволяет запускать файл напрямую из терминала командой: python export_to_sheets.py
    export_data()
