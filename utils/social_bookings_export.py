# social_bookings_export.py
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
import time
from datetime import datetime, timedelta
import pytz
import re
from typing import Optional, Dict, Any
from core.config import GOOGLE_SHEET_KEY, GOOGLE_SHEET_KEY_SECONDARY, GOOGLE_CREDENTIALS_JSON

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Вспомогательная функция для парсинга credentials JSON
def _parse_credentials_json(creds_str):
    """Парсит JSON из строки (поддерживает многострочный и однострочный форматы)."""
    if not creds_str:
        return None
    try:
        return json.loads(creds_str)
    except (json.JSONDecodeError, ValueError):
        try:
            cleaned = " ".join(line.strip() for line in creds_str.split("\n") if line.strip())
            return json.loads(cleaned)
        except Exception as e:
            logging.error("Невозможно парсить GOOGLE_CREDENTIALS_JSON: %s", str(e))
            return None

# ID вкладки "Заявки из Соц сетей"
SOCIAL_BOOKINGS_SHEET_GID = "1842872487"

# ID вкладки дополнительной таблицы "Заявки Соц сети"  
SECONDARY_BOOKINGS_SHEET_GID = "871899838"

# UTM-метки для каждого источника
SOURCE_UTM_DATA = {
    'source_vk': {
        'utm_source': 'vk',
        'utm_medium': 'social',
        'utm_campaign': 'direct',
        'utm_content': 'vkontakte_page',
        'utm_term': 'client_booking'
    },
    'source_inst': {
        'utm_source': 'instagram',
        'utm_medium': 'social',
        'utm_campaign': 'direct',
        'utm_content': 'instagram_account',
        'utm_term': 'client_booking'
    },
    'source_bot_tg': {
        'utm_source': 'telegram',
        'utm_medium': 'bot',
        'utm_campaign': 'direct',
        'utm_content': 'telegram_bot',
        'utm_term': 'bot_booking'
    },
    'source_tg': {
        'utm_source': 'telegram',
        'utm_medium': 'channel',
        'utm_campaign': 'bookevgenich',
        'utm_content': 'telegram_channel',
        'utm_term': 'channel_booking'
    },
    'admin_booking': {
        'utm_source': 'admin',
        'utm_medium': 'manual',
        'utm_campaign': 'admin_booking',
        'utm_content': 'admin_panel_booking',
        'utm_term': 'manager_booking'
    }
}

# UTM-метки для гостевых источников
GUEST_SOURCE_UTM_DATA = {
    'guest_source_yandex': {
        'utm_source': 'yandex',
        'utm_medium': 'organic',
        'utm_campaign': 'guest_booking',
        'utm_content': 'search',
        'utm_term': 'organic_search'
    },
    'guest_source_google': {
        'utm_source': 'google',
        'utm_medium': 'organic',
        'utm_campaign': 'guest_booking',
        'utm_content': 'search',
        'utm_term': 'organic_search'
    },
    'guest_source_2gis': {
        'utm_source': '2gis',
        'utm_medium': 'maps',
        'utm_campaign': 'guest_booking',
        'utm_content': 'maps_listing',
        'utm_term': 'local_search'
    },
    'guest_source_instagram': {
        'utm_source': 'instagram',
        'utm_medium': 'social',
        'utm_campaign': 'guest_booking',
        'utm_content': 'profile_link',
        'utm_term': 'social_organic'
    },
    'guest_source_vkontakte': {
        'utm_source': 'vkontakte',
        'utm_medium': 'social',
        'utm_campaign': 'guest_booking',
        'utm_content': 'profile_link',
        'utm_term': 'social_organic'
    },
    'guest_source_friends': {
        'utm_source': 'word_of_mouth',
        'utm_medium': 'referral',
        'utm_campaign': 'guest_booking',
        'utm_content': 'friends_recommendation',
        'utm_term': 'referral'
    },
    'guest_source_telegram': {
        'utm_source': 'telegram',
        'utm_medium': 'messenger',
        'utm_campaign': 'guest_booking',
        'utm_content': 'bot_booking',
        'utm_term': 'direct_booking'
    },
    'guest_source_other': {
        'utm_source': 'other',
        'utm_medium': 'other',
        'utm_campaign': 'guest_booking',
        'utm_content': 'custom_source',
        'utm_term': 'user_defined'
    }
}

# Объединенные UTM-данные
ALL_SOURCE_UTM_DATA = {**SOURCE_UTM_DATA, **GUEST_SOURCE_UTM_DATA}

# Маппинг источников для отображения
SOURCE_DISPLAY_NAMES = {
    'source_vk': 'ВКонтакте',
    'source_inst': 'Instagram',
    'source_bot_tg': 'Бот в ТГ',
    'source_tg': 'ТГ-канал'
}

# Маппинг гостевых источников для отображения
GUEST_SOURCE_DISPLAY_NAMES = {
    'guest_source_yandex': 'Яндекс',
    'guest_source_google': 'Google',
    'guest_source_2gis': '2ГИС',
    'guest_source_instagram': 'Instagram',
    'guest_source_vkontakte': 'ВКонтакте',
    'guest_source_friends': 'Рассказали друзья',
    'guest_source_telegram': 'Telegram',
    'guest_source_other': 'Другое'
}

# Объединенные названия источников
ALL_SOURCE_DISPLAY_NAMES = {**SOURCE_DISPLAY_NAMES, **GUEST_SOURCE_DISPLAY_NAMES}

def clean_phone_for_sheets(phone: str) -> str:
    """
    Очищает номер телефона для Google Sheets.
    Убирает '+' в начале, чтобы Excel не воспринял как формулу.
    
    Args:
        phone: Номер телефона (может содержать +)
    
    Returns:
        str: Номер без + в начале (через 8 или 7)
    """
    if not phone:
        return ''
    
    # Убираем все пробелы, дефисы, скобки
    cleaned = ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    # Если начинается с +7, заменяем на 8
    if cleaned.startswith('+7'):
        cleaned = '8' + cleaned[2:]
    # Если начинается с +, просто убираем
    elif cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    return cleaned

def get_moscow_time() -> str:
    """
    Возвращает текущее время в московском часовом поясе (UTC+3).
    
    Returns:
        str: Время в формате "dd.mm.yyyy HH:MM"
    """
    try:
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        return moscow_time.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        logging.warning(f"Ошибка получения московского времени: {e}, используем UTC+3")
        # Fallback: UTC + 3 часа
        utc_time = datetime.utcnow()
        moscow_time = utc_time + timedelta(hours=3)
        return moscow_time.strftime('%d.%m.%Y %H:%M')

def parse_booking_date(date_text: str) -> str:
    """
    Преобразует текст даты в формат DD.MM.YYYY.
    Обрабатывает: завтра, послезавтра, дни недели, конкретные даты.
    Поддерживает форматы: "11 Августа", "11 08", "11.08", "в субботу"
    """
    today = datetime.now()
    date_text = date_text.lower().strip()
    
    # Месяцы по названию
    months = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
        'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
        'май': 5, 'июн': 6, 'июл': 7, 'авг': 8,
        'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
    }
    
    # Дни недели (с предлогами и без) и их склонения
    weekdays = {
        'понедельник': 0, 'понедельника': 0, 'пн': 0,
        'вторник': 1, 'вторника': 1, 'вт': 1,
        'среда': 2, 'среду': 2, 'среды': 2, 'ср': 2,
        'четверг': 3, 'четверга': 3, 'чт': 3,
        'пятница': 4, 'пятницу': 4, 'пятницы': 4, 'пт': 4,
        'суббота': 5, 'субботу': 5, 'субботы': 5, 'сб': 5,
        'воскресенье': 6, 'воскресенья': 6, 'вс': 6
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
    
    # Парсим даты с названиями месяцев: "11 августа", "15 июля"
    month_pattern = r'(\d{1,2})\s+([а-яё]+)'
    month_match = re.search(month_pattern, date_text)
    if month_match:
        day = int(month_match.group(1))
        month_name = month_match.group(2).lower()
        
        if month_name in months:
            month = months[month_name]
            year = today.year
            
            try:
                target_date = datetime(year, month, day)
                # Если дата уже прошла в этом году, берем следующий год
                if target_date < today:
                    target_date = datetime(year + 1, month, day)
                return target_date.strftime('%d.%m.%Y')
            except ValueError:
                pass
    
    # Попытка распарсить числовую дату
    # Форматы: 15.08, 15.08.2025, 15/08, 15/08/2025, 15 08
    
    # DD.MM, DD/MM или DD MM (с пробелом)
    date_pattern = r'(\d{1,2})[./ ](\d{1,2})(?:[./](\d{2,4}))?'
    match = re.search(date_pattern, date_text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:  # Если год двузначный
            year += 2000
        
        try:
            target_date = datetime(year, month, day)
            # Если дата уже прошла в этом году, берем следующий год
            if target_date < today and not match.group(3):  # Если год не указан явно
                target_date = datetime(year + 1, month, day)
            return target_date.strftime('%d.%m.%Y')
        except ValueError:
            pass
    
    # Если ничего не распознали, просто возвращаем исходный текст
    return date_text

def parse_booking_time(time_text: str) -> str:
    """
    Преобразует текст времени в формат ЧЧ:ММ.
    Принимает: "19:30", "19.30", "19 30", "1930", "7:30", "7.30"
    """
    time_text = time_text.strip()
    
    # Паттерн для времени: ЧЧ:ММ, ЧЧ.ММ, ЧЧ ММ
    time_pattern = r'(\d{1,2})[:.\s](\d{2})'
    match = re.search(time_pattern, time_text)
    
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        # Валидация времени
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return f"{hours:02d}:{minutes:02d}"
    
    # Паттерн для времени без разделителя: ЧЧЧМ или ЧЧММ
    time_pattern_no_sep = r'^(\d{3,4})$'
    match = re.search(time_pattern_no_sep, time_text)
    
    if match:
        time_str = match.group(1)
        if len(time_str) == 3:  # ЧЧМ -> Ч:ММ
            hours = int(time_str[0])
            minutes = int(time_str[1:3])
        elif len(time_str) == 4:  # ЧЧММ
            hours = int(time_str[0:2])
            minutes = int(time_str[2:4])
        else:
            return time_text
            
        # Валидация времени
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return f"{hours:02d}:{minutes:02d}"
    
    # Если ничего не распознали, возвращаем исходный текст
    return time_text

def get_admin_name_by_id(admin_id: int) -> str:
    """Возвращает Telegram-тег админа по его ID."""
    # Словарь админов с их Telegram-тегами
    admin_tags = {
        196614680: "@nilfts",
        208281210: "@kristina_evgenich",
        1334453330: "@xquerel",
        12345678: "@test_admin"
    }
    return admin_tags.get(admin_id, f"@admin_{admin_id}")

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
        # GOOGLE_CREDENTIALS_JSON уже распарсен в config.py как dict
        credentials_info = GOOGLE_CREDENTIALS_JSON if isinstance(GOOGLE_CREDENTIALS_JSON, dict) else json.loads(GOOGLE_CREDENTIALS_JSON)
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
        creation_datetime = get_moscow_time()  # Московское время UTC+3
        
        # Парсим дату бронирования
        booking_date = parse_booking_date(booking_data.get('date', ''))
        
        # Маппинг источников трафика для отображения
        source_mapping = {
            'source_vk': 'ВКонтакте',
            'source_inst': 'Instagram', 
            'source_bot_tg': 'Бот в ТГ',
            'source_tg': 'Забронируй Евгенича'
        }
        
        # Маппинг источников трафика для тегов АМО
        amo_tag_mapping = {
            'source_vk': 'vk',
            'source_inst': 'inst', 
            'source_bot_tg': 'bot_tg',
            'source_tg': 'tg'
        }
        
        # Расширенный маппинг UTM-меток (полная структура как на сайте)
        utm_mapping = {
            'source_vk': {
                'utm_source': 'vk',                    # соответствует АМО тегу
                'utm_medium': 'social',
                'utm_campaign': 'admin_booking',
                'utm_content': 'admin_panel_booking',
                'utm_term': 'vk_social_booking'
            },
            'source_inst': {
                'utm_source': 'inst',                  # соответствует АМО тегу  
                'utm_medium': 'social', 
                'utm_campaign': 'admin_booking',
                'utm_content': 'admin_panel_booking',
                'utm_term': 'instagram_social_booking'
            },
            'source_bot_tg': {
                'utm_source': 'bot_tg',                # соответствует АМО тегу
                'utm_medium': 'bot',
                'utm_campaign': 'direct',
                'utm_content': 'telegram_bot',
                'utm_term': 'direct_booking'
            },
            'source_tg': {
                'utm_source': 'tg',                    # соответствует АМО тегу
                'utm_medium': 'channel',
                'utm_campaign': 'bookevgenich',
                'utm_content': 'telegram_channel',
                'utm_term': 'channel_booking'
            }
        }
        
        source_display = source_mapping.get(booking_data.get('source', ''), booking_data.get('source', 'Неизвестно'))
        # Если amo_tag уже установлен (код бара), используем его. Иначе берём от источника
        amo_tag = booking_data.get('amo_tag') or amo_tag_mapping.get(booking_data.get('source', ''), 'unknown')
        admin_name = get_admin_name_by_id(admin_id)
        
        # Получаем UTM-данные для источника
        source = booking_data.get('source', '')
        utm_data = utm_mapping.get(source, {
            'utm_source': '',
            'utm_medium': '',
            'utm_campaign': '',
            'utm_content': '',
            'utm_term': ''
        })
        
        # Объединяем дату и время в одну колонку
        datetime_combined = f"{booking_date} {booking_data.get('time', '')}" if booking_data.get('time', '') else booking_date
        
        # Формируем строку для добавления (дата и время объединены, колонки сдвинуты)
        row_data = [
            creation_datetime,                      # A: Дата Заявки
            booking_data.get('name', ''),           # B: Имя Гостя
            clean_phone_for_sheets(booking_data.get('phone', '')),  # C: Телефон (без +)
            datetime_combined,                      # D: Дата и время посещения
            booking_data.get('guests', ''),         # E: Кол-во гостей (было F)
            source_display,                         # F: Источник (было G)
            amo_tag,                                # G: ТЕГ для АМО (было H) - теперь код бара
            admin_name,                             # H: Кто создал заявку (было J)
            'Новая',                                # I: Статус (было K)
            utm_data.get('utm_source', ''),         # J: UTM Source (было L)
            utm_data.get('utm_medium', ''),         # K: UTM Medium (было M)
            utm_data.get('utm_campaign', ''),       # L: UTM Campaign (было N)
            utm_data.get('utm_content', ''),        # M: UTM Content (было O)
            utm_data.get('utm_term', ''),           # N: UTM Term (было P)
            f"BID-{int(time.time())}",              # O: ID заявки (было Q)
            admin_id                                # P: Telegram ID создателя (было R)
        ]
        
        # Добавляем строку в таблицу
        worksheet.append_row(row_data)
        
        logging.info(f"Заявка успешно экспортирована в таблицу. Клиент: {booking_data.get('name', '')}, Админ: {admin_name}")
        
        # Также экспортируем в дополнительную таблицу
        try:
            export_booking_to_secondary_table(booking_data, admin_id, is_admin_booking=True)
        except Exception as e:
            logging.error(f"Ошибка экспорта в дополнительную таблицу: {e}")
        
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при экспорте заявки в Google Sheets: {e}")
        return False

def export_guest_booking_to_sheets(booking_data: Dict[str, Any], user_id: int = None) -> bool:
    """
    Экспортирует данные гостевого бронирования в Google Sheets на вкладку "Заявки из Соц сетей".
    
    Args:
        booking_data: Словарь с данными гостевого бронирования (без источника)
        user_id: Telegram ID пользователя, который создал заявку (опционально)
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        # Подключение к Google Sheets
        # GOOGLE_CREDENTIALS_JSON уже распарсен в config.py как dict
        credentials_info = GOOGLE_CREDENTIALS_JSON if isinstance(GOOGLE_CREDENTIALS_JSON, dict) else json.loads(GOOGLE_CREDENTIALS_JSON)
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
        creation_datetime = get_moscow_time()  # Московское время UTC+3
        
        # Парсим дату бронирования
        booking_date = parse_booking_date(booking_data.get('date', ''))
        
        # Для гостевых бронирований без источника используем специальные значения
        source_display = "🤖 Гостевое бронирование (бот)"
        amo_tag = booking_data.get('amo_tag', 'guest_bot')  # Код бара или 'guest_bot' если не указан
        creator_name = "👤 Посетитель (через бота)"
        
        # UTM-данные для гостевого бронирования через бота
        utm_data = {
            'utm_source': 'bot_tg',
            'utm_medium': 'guest_booking',
            'utm_campaign': 'direct_guest',
            'utm_content': 'bot_guest_booking',
            'utm_term': 'guest_direct'
        }
        
        # Объединяем дату и время в одну колонку
        datetime_combined = f"{booking_date} {booking_data.get('time', '')}" if booking_data.get('time', '') else booking_date
        
        # Формируем строку для добавления
        # Формируем строку для добавления (дата и время объединены, колонки сдвинуты)
        row_data = [
            creation_datetime,                      # A: Дата Заявки
            booking_data.get('name', ''),           # B: Имя Гостя
            clean_phone_for_sheets(booking_data.get('phone', '')),  # C: Телефон (без +)
            datetime_combined,                      # D: Дата и время посещения
            booking_data.get('guests', ''),         # E: Кол-во гостей (было F)
            source_display,                         # F: Источник (было G)
            amo_tag,                                # G: ТЕГ для АМО (было H) - теперь код бара
            creator_name,                           # H: Кто создал заявку (было J)
            'Новая',                                # I: Статус (было K)
            utm_data.get('utm_source', ''),         # J: UTM Source (было L)
            utm_data.get('utm_medium', ''),         # K: UTM Medium (было M)
            utm_data.get('utm_campaign', ''),       # L: UTM Campaign (было N)
            utm_data.get('utm_content', ''),        # M: UTM Content (было O)
            utm_data.get('utm_term', ''),           # N: UTM Term (было P)
            f"BID-{int(time.time())}",              # O: ID заявки (было Q)
            user_id if user_id else ""              # P: Telegram ID создателя (было R)
        ]
        
        # Проверяем корректность данных
        for i, value in enumerate(row_data):
            if value is None:
                row_data[i] = ""
            elif not isinstance(value, (str, int, float)):
                row_data[i] = str(value)
        
        logging.info(f"Подготовлена строка для экспорта: {len(row_data)} колонок")
        
        # Добавляем строку в таблицу
        try:
            logging.info(f"Добавляем гостевую заявку в таблицу. Данные: {len(row_data)} колонок")
            worksheet.append_row(row_data)
            logging.info(f"Гостевая заявка успешно экспортирована в таблицу. Клиент: {booking_data.get('name', '')}")
        except Exception as append_error:
            logging.error(f"Ошибка при добавлении строки в Google Sheets: {append_error}")
            logging.error(f"Данные строки: {row_data}")
            raise append_error
        
        # Также экспортируем в дополнительную таблицу
        try:
            export_booking_to_secondary_table(booking_data, user_id, is_admin_booking=False)
        except Exception as e:
            logging.error(f"Ошибка экспорта в дополнительную таблицу: {e}")
        
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при экспорте гостевой заявки в Google Sheets: {e}")
        return False

def export_booking_to_secondary_table(booking_data: Dict[str, Any], user_id: int, is_admin_booking: bool = False) -> bool:
    """
    Экспортирует заявку в дополнительную таблицу с упрощенной структурой.
    
    Args:
        booking_data: Словарь с данными бронирования
        user_id: Telegram ID создателя заявки
        is_admin_booking: Флаг админской заявки (для определения канала)
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    logging.info(f"🔄 Начинаю экспорт во вторую таблицу: user_id={user_id}, is_admin={is_admin_booking}")
    
    if not GOOGLE_SHEET_KEY_SECONDARY:
        logging.warning("❌ Дополнительная таблица не настроена - GOOGLE_SHEET_KEY_SECONDARY отсутствует")
        return False
        
    try:
        # Подключение к Google Sheets
        # GOOGLE_CREDENTIALS_JSON уже распарсен в config.py как dict
        credentials_info = GOOGLE_CREDENTIALS_JSON if isinstance(GOOGLE_CREDENTIALS_JSON, dict) else _parse_credentials_json(GOOGLE_CREDENTIALS_JSON)
        if not credentials_info:
            logging.error("Не удалось парсить GOOGLE_CREDENTIALS_JSON")
            return False
        
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(GOOGLE_SHEET_KEY_SECONDARY)
        
        # Отладочная информация
        logging.info(f"Открыта дополнительная таблица с ключом: {GOOGLE_SHEET_KEY_SECONDARY}")
        logging.info(f"Доступные вкладки: {[f'{ws.title} (id={ws.id})' for ws in sheet.worksheets()]}")
        
        # Открываем нужную вкладку по gid
        worksheet = None
        for ws in sheet.worksheets():
            if str(ws.id) == SECONDARY_BOOKINGS_SHEET_GID:
                worksheet = ws
                break
        
        if not worksheet:
            logging.error(f"❌ Не найдена вкладка с gid={SECONDARY_BOOKINGS_SHEET_GID} в дополнительной таблице")
            logging.error(f"🔍 Доступные вкладки: {[f'{ws.title} (id={ws.id})' for ws in sheet.worksheets()]}")
            return False
        
        logging.info(f"✅ Найдена вкладка: {worksheet.title} (id={worksheet.id})")
        
        # Проверяем количество колонок в таблице
        try:
            headers = worksheet.row_values(1)
            logging.info(f"📋 Заголовки в таблице: {len(headers)} колонок")
            logging.info(f"📋 Заголовки: {headers}")
        except Exception as header_error:
            logging.warning(f"⚠️ Не удалось получить заголовки: {header_error}")
        
        # Обработка данных
        creation_datetime = get_moscow_time()  # Московское время UTC+3
        
        # Парсим дату бронирования
        booking_date = parse_booking_date(booking_data.get('date', ''))
        
        # Объединяем дату и время
        datetime_combined = f"{booking_date} {booking_data.get('time', '')}" if booking_data.get('time', '') else booking_date
        
        # Определяем канал и создателя
        if is_admin_booking:
            channel = "Админ-панель"
            creator_name = get_admin_name_by_id(user_id)
        else:
            channel = "Гостевое бронирование"
            creator_name = "👤 Посетитель (через бота)"
        
        # Получаем UTM-данные
        if is_admin_booking:
            source = booking_data.get('source', '')
            utm_mapping = {
                'source_vk': {
                    'utm_source': 'vk',
                    'utm_medium': 'social',
                    'utm_campaign': 'admin_booking',
                    'utm_content': 'admin_panel_booking',
                    'utm_term': 'vk_social_booking'
                },
                'source_inst': {
                    'utm_source': 'inst',
                    'utm_medium': 'social', 
                    'utm_campaign': 'admin_booking',
                    'utm_content': 'admin_panel_booking',
                    'utm_term': 'instagram_social_booking'
                },
                'source_bot_tg': {
                    'utm_source': 'bot_tg',
                    'utm_medium': 'bot',
                    'utm_campaign': 'direct',
                    'utm_content': 'telegram_bot',
                    'utm_term': 'direct_booking'
                },
                'source_tg': {
                    'utm_source': 'tg',
                    'utm_medium': 'channel',
                    'utm_campaign': 'bookevgenich',
                    'utm_content': 'telegram_channel',
                    'utm_term': 'channel_booking'
                }
            }
            utm_data = utm_mapping.get(source, {
                'utm_source': '',
                'utm_medium': '',
                'utm_campaign': '',
                'utm_content': '',
                'utm_term': ''
            })
        else:
            # Для гостевых бронирований
            utm_data = {
                'utm_source': 'bot_tg',
                'utm_medium': 'guest_booking', 
                'utm_campaign': 'direct_guest',
                'utm_content': 'bot_guest_booking',
                'utm_term': 'guest_direct'
            }
        
        # Определяем тег бара по полю 'bar'
        bar_tags = {
            'bar_nevsky': 'ЕВГ_СПБ_НЕВ',
            'bar_rubinstein': 'ЕВГ_СПБ_РУБ',
            'bar_pyatnitskaya': 'ЕВГ_МСК_ПЯТ',
            'bar_tsvetnoj': 'ЕВГ_МСК_ЦВЕТ'
        }
        bar_tag = bar_tags.get(booking_data.get('bar', ''), 'ЕВГ_СПБ_НЕВ')
        
        # Формируем строку для новой таблицы (колонки A-R)
        # Генерируем название сделки: TAG (имя) номер
        # Очищаем телефон от + для Excel
        clean_phone = clean_phone_for_sheets(booking_data.get('phone', ''))
        deal_name = f"{bar_tag} ({booking_data.get('name', '')}) {clean_phone}"
        
        row_data = [
            deal_name,                              # A: Сделка.Название
            datetime_combined,                      # B: Сделка.Время прихода
            booking_data.get('guests', ''),         # C: Сделка.Кол-во гостей
            utm_data.get('utm_source', ''),         # D: Сделка.R.Источник сделки
            bar_tag,                                # E: Сделка.R.Тег города (код бара)
            booking_data.get('name', ''),           # F: Контакт.ФИО
            clean_phone,                            # G: Контакт.Телефон (без +)
            '',                                     # H: Резерв (было "Повод")
            utm_data.get('utm_medium', ''),         # I: UTM Medium (Канал)
            utm_data.get('utm_campaign', ''),       # J: UTM Campaign (Кампания)
            utm_data.get('utm_content', ''),        # K: UTM Content (Содержание)
            utm_data.get('utm_term', ''),           # L: UTM Term (Ключ/Дата)
            user_id,                                # M: ID username
            creation_datetime,                      # N: Дата Заявки
            channel,                                # O: Канал
            creator_name,                           # P: Кто создал заявку
            'Новая',                                # Q: Статус
            f"BID-{int(time.time())}"               # R: ID us
        ]
        
        # Проверяем и валидируем данные
        if len(row_data) != 18:
            logging.error(f"❌ Неправильное количество колонок: {len(row_data)}, ожидается 18")
            return False
        
        # Валидация типов данных
        for i, value in enumerate(row_data):
            if value is None:
                row_data[i] = ""
            elif not isinstance(value, (str, int, float)):
                row_data[i] = str(value)
        
        # Добавляем строку в таблицу
        logging.info(f"📊 Подготовленная строка для второй таблицы: {len(row_data)} колонок (A-R)")
        logging.info(f"📊 Данные: {row_data[:3]}...{row_data[-3:]}")  # Показываем первые и последние элементы
        
        try:
            logging.info("🔄 Начинаю запись в таблицу...")
            worksheet.append_row(row_data)
            logging.info("✅ Строка успешно записана в таблицу")
        except Exception as append_error:
            logging.error(f"❌ Ошибка при записи в таблицу: {append_error}")
            logging.error(f"❌ Тип ошибки: {type(append_error)}")
            raise append_error
        
        logging.info(f"✅ Заявка успешно экспортирована в дополнительную таблицу. Клиент: {booking_data.get('name', '')}, TG ID: {user_id}")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при экспорте заявки в дополнительную таблицу: {e}")
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
