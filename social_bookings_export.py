# social_bookings_export.py
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
from datetime import datetime, timedelta
import re
from typing import Optional, Dict, Any
from config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ID вкладки "Заявки из Соц сетей"
SOCIAL_BOOKINGS_SHEET_GID = "1842872487"

def parse_booking_date(date_text: str) -> str:
    """
    Преобразует текст даты в формат DD.MM.YYYY.
    Обрабатывает: завтра, послезавтра, дни недели, конкретные даты.
    """
    today = datetime.now()
    date_text = date_text.lower().strip()
    
    # Дни недели (с предлогами и без) и их склонения
    weekdays = {
        'понедельник': 0, 'понедельник': 0,
        'вторник': 1, 'вторник': 1,
        'среда': 2, 'среду': 2,
        'четверг': 3, 'четверг': 3,
        'пятница': 4, 'пятницу': 4,
        'суббота': 5, 'субботу': 5,
        'воскресенье': 6, 'воскресенье': 6,
        'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5, 'вс': 6
    }
    
    # Сегодня
    if 'сегодня' in date_text:
        return today.strftime('%d.%m.%Y')
    
    # Завтра
    if 'завтра' in date_text and 'послезавтра' not in date_text:
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime('%d.%m.%Y')
    
    # Послезавтра
    if 'послезавтра' in date_text:
        day_after_tomorrow = today + timedelta(days=2)
        return day_after_tomorrow.strftime('%d.%m.%Y')
    
    # Дни недели (учитываем предлоги)
    for day_name, day_num in weekdays.items():
        # Проверяем разные варианты написания
        patterns = [day_name, f"в {day_name}", f"во {day_name}"]
        for pattern in patterns:
            if pattern in date_text:
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # Если день уже прошел на этой неделе, берем следующую неделю
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%d.%m.%Y')
    
    # Попытка распарсить числовую дату
    # Форматы: 15.08, 15.08.2025, 15/08, 15/08/2025, 15 августа и т.д.
    
    # DD.MM или DD/MM
    date_pattern = r'(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?'
    match = re.search(date_pattern, date_text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:  # Если год двузначный
            year += 2000
        
        try:
            target_date = datetime(year, month, day)
            return target_date.strftime('%d.%m.%Y')
        except ValueError:
            pass
    
    # Если ничего не распознали, просто возвращаем исходный текст
    return date_text

def get_admin_name_by_id(admin_id: int) -> str:
    """Возвращает имя админа по его ID."""
    # Словарь админов (можно вынести в config)
    admin_names = {
        196614680: "Нил Владимирович",
        208281210: "Кристина",
        12345678: "Тест Сотрудникович"
    }
    return admin_names.get(admin_id, f"Админ {admin_id}")

def export_social_booking_to_sheets(booking_data: Dict[str, Any], admin_id: int) -> bool:
    """
    Экспортирует данные админской брони в Google Sheets на вкладку "Заявки из Соц сетей".
    
    Args:
        booking_data: Словарь с данными брони
        admin_id: ID админа, создавшего заявку
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        # Подключение к Google Sheets
        credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        
        # Открываем нужную вкладку по gid
        worksheet = None
        for ws in sheet.worksheets():
            if str(ws.id) == SOCIAL_BOOKINGS_SHEET_GID:
                worksheet = ws
                break
        
        if not worksheet:
            logging.error(f"Не найдена вкладка с gid={SOCIAL_BOOKINGS_SHEET_GID}")
            return False
        
        # Обработка данных
        now = datetime.now()
        creation_datetime = now.strftime('%d.%m.%Y %H:%M')
        
        # Парсим дату бронирования
        booking_date = parse_booking_date(booking_data.get('date', ''))
        
        # Маппинг источников трафика
        source_mapping = {
            'source_vk': 'ВКонтакте',
            'source_instagram': 'Instagram', 
            'source_tg_booking': 'ТГ-чат броней',
            'source_tg_channel': 'ТГ-канал'
        }
        
        source_display = source_mapping.get(booking_data.get('source', ''), booking_data.get('source', 'Неизвестно'))
        admin_name = get_admin_name_by_id(admin_id)
        
        # Формируем строку для добавления
        row_data = [
            creation_datetime,          # Дата и время создания
            booking_data.get('name', ''),           # Имя клиента
            booking_data.get('phone', ''),          # Телефон
            booking_date,                           # Дата бронирования
            booking_data.get('time', ''),           # Время бронирования
            booking_data.get('guests', ''),         # Количество гостей
            source_display,                         # Источник трафика
            booking_data.get('reason', ''),         # Повод
            admin_name,                             # Кто создал заявку
            'Новая'                                 # Статус
        ]
        
        # Добавляем строку в таблицу
        worksheet.append_row(row_data)
        
        logging.info(f"Заявка успешно экспортирована в таблицу. Клиент: {booking_data.get('name', '')}, Админ: {admin_name}")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при экспорте заявки в Google Sheets: {e}")
        return False

def test_date_parsing():
    """Тестовая функция для проверки парсинга дат."""
    test_dates = [
        "завтра", "послезавтра", "в субботу", "в понедельник", 
        "15.08", "15.08.2025", "15/08", "15 августа", "сегодня"
    ]
    
    print("Тестирование парсинга дат:")
    for date_str in test_dates:
        parsed = parse_booking_date(date_str)
        print(f"'{date_str}' -> '{parsed}'")

if __name__ == "__main__":
    test_date_parsing()
