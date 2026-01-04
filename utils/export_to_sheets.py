# export_to_sheets.py
import sqlite3
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
from typing import Tuple
from datetime import datetime
from core.config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON, DATABASE_PATH

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Вспомогательная функция для валидации JSON ---
def _parse_credentials_json(creds) -> Tuple[bool, dict, str]:
    """
    Парсит JSON из строки или принимает уже распарсенный dict.
    Возвращает (успех, словарь_данных, сообщение_ошибки).
    """
    if not creds:
        return False, {}, "Переменная GOOGLE_CREDENTIALS_JSON пуста"

    # Если уже dict — возвращаем напрямую
    if isinstance(creds, dict):
        return True, creds, ""

    # Если строка — пытаемся распарсить
    if isinstance(creds, str):
        try:
            return True, json.loads(creds), ""
        except (json.JSONDecodeError, ValueError):
            try:
                cleaned = " ".join(line.strip() for line in creds.splitlines() if line.strip())
                return True, json.loads(cleaned), ""
            except Exception as e2:
                return False, {}, f"Невозможно парсить GOOGLE_CREDENTIALS_JSON: {str(e2)}"

    return False, {}, "Неподдерживаемый формат GOOGLE_CREDENTIALS_JSON"

# --- Настройки ---
DB_FILE = DATABASE_PATH  # Используем путь из переменной окружения
EXPORT_SHEET_NAME = "Выгрузка Пользователей" 

# --- Конфигурация столбцов ---
COLUMN_CONFIG = {
    "signup_date": "Дата Регистрации",
    "user_id": "ID Пользователя", 
    "first_name": "Имя в Telegram",
    "username": "Юзернейм в Telegram",
    "phone_number": "Номер Телефона",
    "contact_shared_date": "Дата Предоставления Контакта",
    "real_name": "Настоящее Имя",
    "birth_date": "Дата Рождения",
    "profile_completed": "Профиль Завершен",
    "status": "Статус Награды",
    "display_source": "Источник Привлечения",
    "referrer_id": "ID Пригласившего", 
    "redeem_date": "Дата Погашения",
    "staff_full_name": "Сотрудник (полное имя)"
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
        cur.execute("""
            SELECT u.*, 
                   CASE 
                       WHEN u.source = 'staff' AND u.brought_by_staff_id IS NOT NULL 
                       THEN 'Сотрудник: ' || s.short_name
                       ELSE u.source 
                   END as display_source,
                   s.full_name as staff_full_name
            FROM users u
            LEFT JOIN staff s ON u.brought_by_staff_id = s.staff_id
            ORDER BY u.signup_date DESC
        """)
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
        success, creds_dict, error_msg = _parse_credentials_json(GOOGLE_CREDENTIALS_JSON)
        if not success:
            msg = f"Ошибка парсинга GOOGLE_CREDENTIALS_JSON: {error_msg}"
            logging.error(msg)
            return False, msg
        
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        
        # Попытка получить лист по названию
        try:
            worksheet = spreadsheet.worksheet(EXPORT_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Лист не найден — логируем доступные и пробуем найти по нечувствительному к регистру
            logging.warning(f"Лист '{EXPORT_SHEET_NAME}' не найден. Ищу среди доступных вкладок:")
            worksheet = None
            for ws in spreadsheet.worksheets():
                logging.warning(f"  - {ws.title} (id={ws.id})")
                # Попробуем найти по нечувствительному к регистру совпадению
                if ws.title.strip().lower() == EXPORT_SHEET_NAME.strip().lower():
                    logging.info(f"Найдена вкладка по нечувствительному к регистру: {ws.title}")
                    worksheet = ws
                    break
            
            if not worksheet:
                # Не найдена — попробуем создать
                try:
                    logging.info(f"Пытаюсь создать вкладку '{EXPORT_SHEET_NAME}' автоматически.")
                    worksheet = spreadsheet.add_worksheet(title=EXPORT_SHEET_NAME, rows=200, cols=20)
                    logging.info(f"Вкладка '{EXPORT_SHEET_NAME}' успешно создана")
                except Exception as ce:
                    msg = f"Не удалось создать вкладку '{EXPORT_SHEET_NAME}': {ce}"
                    logging.error(msg)
                    return False, msg
        
        logging.info("Успешное подключение к Google Sheets.")
    except Exception as e:
        msg = f"Не удалось подключиться к Google Sheets: {e}"
        logging.error(msg)
        return False, msg

    try:
        # Не очищаем существующие строки — будем дописывать только новые записи
        header_row = list(COLUMN_CONFIG.values())
        column_order_keys = list(COLUMN_CONFIG.keys())

        # Получим текущие значения листа, чтобы не затирать старые
        existing_values = worksheet.get_all_values()

        # Если лист пустой или нет заголовка — запишем заголовок и все строки
        if not existing_values or len(existing_values) == 0:
            logging.info("Лист пустой — записываю заголовок и все строки.")
            data_to_upload = [header_row]
            for user_row in users:
                ordered_row = []
                for key in column_order_keys:
                    value = user_row[key]
                    if key == 'profile_completed':
                        value = "Да" if value == 1 else "Нет"
                    if isinstance(value, str) and ('-' in value and ':' in value):
                        try:
                            value = datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            pass
                    ordered_row.append(value)
                data_to_upload.append(ordered_row)
            worksheet.update(data_to_upload, 'A1')
            msg = f"УСПЕХ! Данные ({len(data_to_upload)} строк) успешно выгружены."
            logging.info(msg)
            return True, msg

        # Есть данные — определим индекс столбца с ID Пользователя и соберём существующие id
        header_vals = existing_values[0]
        header_lower = [h.strip().lower() for h in header_vals]
        id_col_label = COLUMN_CONFIG.get('user_id', 'ID Пользователя')
        id_col_label_lower = id_col_label.strip().lower()
        try:
            id_col_index = header_lower.index(id_col_label_lower)
        except ValueError:
            id_col_index = None

        existing_ids = set()
        if id_col_index is not None:
            for row in existing_values[1:]:
                if len(row) > id_col_index and row[id_col_index].strip():
                    try:
                        existing_ids.add(int(row[id_col_index]))
                    except Exception:
                        pass

        # Подготовим только новые строки (которые ещё не в листе)
        new_rows = []
        for user_row in users:
            uid = user_row['user_id']
            if uid in existing_ids:
                continue
            ordered_row = []
            for key in column_order_keys:
                value = user_row[key]
                if key == 'profile_completed':
                    value = "Да" if value == 1 else "Нет"
                if isinstance(value, str) and ('-' in value and ':' in value):
                    try:
                        value = datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
                ordered_row.append(value)
            new_rows.append(ordered_row)

        if not new_rows:
            msg = "Нет новых пользователей для добавления — экспорт пропущен."
            logging.info(msg)
            return True, msg

        # Дописываем новые строки в конец листа
        try:
            worksheet.append_rows(new_rows, value_input_option='USER_ENTERED')
        except TypeError:
            # Старые версии gspread могут не поддерживать value_input_option
            worksheet.append_rows(new_rows)

        msg = f"УСПЕХ! Добавлено {len(new_rows)} новых строк."
        logging.info(msg)
        return True, msg
    except Exception as e:
        msg = f"Ошибка при выгрузке данных в Google Sheets: {e}"
        logging.error(msg)
        return False, msg

if __name__ == '__main__':
    success, message = do_export()
    print(message)
