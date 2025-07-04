import logging
import json
import datetime
from typing import Optional
import pytz  # Импортируем новую библиотеку

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
    # ... (эта функция остается без изменений) ...

def find_user_by_id(user_id: int) -> Optional[gspread.Cell]:
    # ... (эта функция остается без изменений) ...

def get_reward_status(user_id: int) -> str:
    # ... (эта функция остается без изменений) ...

def add_new_user(user_id: int, username: str, first_name: str):
    """Добавляет нового пользователя, сохраняя время в UTC."""
    try:
        worksheet = get_sheet()
        if not worksheet: return

        # Сохраняем время в универсальном формате UTC
        current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        if not worksheet.get_all_values():
             headers = ['Дата подписки (UTC)', 'ID Пользователя', 'Username', 'Имя', 'Статус награды']
             worksheet.delete_rows(1) # Очищаем лист на случай если он был создан, но пуст
             worksheet.insert_row(headers, 1)
             worksheet.format('A1:E1', {'textFormat': {'bold': True}})

        row_to_add = [current_time_utc, user_id, username, first_name, 'issued']
        worksheet.append_row(row_to_add)
        logging.info(f"Пользователь {user_id} (@{username}) успешно добавлен в Google Таблицу.")
    except Exception as e:
        logging.error(f"Не удалось добавить пользователя {user_id} в Google Таблицу: {e}")

def redeem_reward(user_id: int) -> bool:
    # ... (эта функция остается без изменений) ...

def get_daily_report_data() -> (int, int):
    """Собирает данные для отчета, используя МОСКОВСКОЕ ВРЕМЯ."""
    try:
        worksheet = get_sheet()
        if not worksheet: return 0, 0

        all_records = worksheet.get_all_records()
        
        # Устанавливаем часовой пояс Москвы
        tz_moscow = pytz.timezone('Europe/Moscow')
        
        # Определяем временные рамки смены по МОСКОВСКОМУ времени
        now_moscow = datetime.datetime.now(tz_moscow)
        
        end_of_shift = now_moscow.replace(hour=6, minute=0, second=0, microsecond=0)
        # Если сейчас раньше 6 утра, значит, рабочая смена еще вчерашняя
        if now_moscow.hour < 6:
            start_of_shift = (end_of_shift - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        else: # Иначе смена уже сегодняшняя
            start_of_shift = now_moscow.replace(hour=12, minute=0, second=0, microsecond=0)
            # Конец смены будет в 6 утра следующего дня
            end_of_shift = (start_of_shift + datetime.timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

        issued_count = 0
        redeemed_count = 0

        for record in all_records:
            try:
                # Записи в таблице хранятся в UTC. Приводим их к этому формату для сравнения.
                record_time_naive = datetime.datetime.strptime(record['Дата подписки (UTC)'], "%Y-%m-%d %H:%M:%S")
                record_time_utc = pytz.utc.localize(record_time_naive)

                # Сравниваем время в одном и том же стандарте
                if start_of_shift <= record_time_utc < end_of_shift:
                    issued_count += 1
                    if record['Статус награды'] == 'redeemed':
                        redeemed_count += 1
            except (ValueError, TypeError, KeyError):
                continue 

        return issued_count, redeemed_count
    except Exception as e:
        logging.error(f"Ошибка при сборе данных для отчета: {e}")
        return 0, 0
