#!/usr/bin/env python3
"""
Тест экспорта во вторую таблицу с подробной отладкой
"""
import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials

# Эмулируем переменные окружения
os.environ["BOT_TOKEN"] = "test"
os.environ["CHANNEL_ID"] = "test"
os.environ["ADMIN_IDS"] = "196614680"
os.environ["HELLO_STICKER_ID"] = "test"
os.environ["NASTOYKA_STICKER_ID"] = "test"
os.environ["THANK_YOU_STICKER_ID"] = "test"

# Используем переменные окружения для доступа к Google Sheets (если есть)
# В реальной среде эти переменные уже должны быть установлены

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_secondary_table_connection():
    """Тестирует подключение ко второй таблице"""
    print("🔗 Тестирование подключения ко второй таблице\n")
    
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        print("❌ GOOGLE_CREDENTIALS_JSON не установлен")
        return
    
    try:
        # Подключаемся напрямую
        credentials_info = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        
        # Ключ второй таблицы
        secondary_key = "1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4"
        sheet = gc.open_by_key(secondary_key)
        
        print(f"✅ Подключение ко второй таблице успешно!")
        print(f"📊 Название таблицы: {sheet.title}")
        print(f"🔍 Доступные вкладки:")
        
        target_gid = "871899838"
        target_worksheet = None
        
        for ws in sheet.worksheets():
            print(f"   - {ws.title} (id={ws.id})")
            if str(ws.id) == target_gid:
                target_worksheet = ws
        
        if target_worksheet:
            print(f"✅ Найдена целевая вкладка: {target_worksheet.title} (id={target_worksheet.id})")
            
            # Проверяем заголовки
            headers = target_worksheet.row_values(1)
            print(f"📋 Заголовки ({len(headers)} колонок):")
            for i, header in enumerate(headers, 1):
                col_letter = chr(64 + i)  # A=65, B=66, etc.
                print(f"   {col_letter}: {header}")
                
        else:
            print(f"❌ Не найдена вкладка с gid={target_gid}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

def test_data_structure():
    """Тестирует структуру данных для экспорта"""  
    print("\n📊 Тестирование структуры данных для экспорта\n")
    
    # Тестовые данные
    booking_data = {
        'name': 'Тест Экспорт Вторая',
        'phone': '+7(999)888-77-66',
        'date': '30.07.2025',
        'time': '20:00',
        'guests': '3',
        'reason': 'Корпоратив',
        'source': 'source_vk'
    }
    
    user_id = 196614680
    is_admin_booking = True
    
    # Эмулируем создание данных как в коде
    from datetime import datetime
    import time
    
    creation_datetime = datetime.now().strftime('%d.%m.%Y %H:%M')
    datetime_combined = f"{booking_data.get('date', '')} {booking_data.get('time', '')}"
    
    if is_admin_booking:
        channel = "Админ-панель"
        creator_name = "Нил Михайлюк"
    else:
        channel = "Гостевое бронирование"
        creator_name = "👤 Посетитель (через бота)"
    
    utm_data = {
        'utm_source': 'vk',
        'utm_medium': 'social',
        'utm_campaign': 'direct',
        'utm_content': 'vkontakte_page',
        'utm_term': 'client_booking'
    }
    
    # Формируем строку для новой таблицы (колонки A-P)
    row_data = [
        creation_datetime,                      # A: Дата Заявки
        channel,                                # B: Канал
        creator_name,                           # C: Кто создал заявку
        'Новая',                                # D: Статус
        f"BID-{int(time.time())}",              # E: ID us (ID заявки)
        booking_data.get('name', ''),           # F: Имя Гостя
        booking_data.get('phone', ''),          # G: Телефон
        datetime_combined,                      # H: Дата / Время
        booking_data.get('guests', ''),         # I: Кол-во гостей
        booking_data.get('reason', ''),         # J: Повод Визита
        utm_data.get('utm_source', ''),         # K: UTM Source (Источник)
        utm_data.get('utm_medium', ''),         # L: UTM Medium (Канал)
        utm_data.get('utm_campaign', ''),       # M: UTM Campaign (Кампания)
        utm_data.get('utm_content', ''),        # N: UTM Content (Содержание)
        utm_data.get('utm_term', ''),           # O: UTM Term (Ключ/Дата)
        user_id                                 # P: ID TG
    ]
    
    print(f"Подготовленная строка: {len(row_data)} колонок")
    print("Данные для экспорта:")
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    for i, (col, value) in enumerate(zip(columns, row_data)):
        print(f"   {col}: {value}")

if __name__ == "__main__":
    print("🚀 Тестирование второй таблицы\n")
    
    test_secondary_table_connection()
    test_data_structure()
    
    print("\n🏁 Тестирование завершено!")

def test_data_structure():
    """Тестирует структуру данных для экспорта"""
    print("\n📊 Тестирование структуры данных для экспорта\n")
    
    # Тестовые данные
    booking_data = {
        'name': 'Тест Экспорт Вторая',
        'phone': '+7(999)888-77-66',
        'date': '30.07.2025',
        'time': '20:00',
        'guests': '3',
        'reason': 'Корпоратив',
        'source': 'source_vk'
    }
    
    user_id = 196614680
    is_admin_booking = True
    
    # Эмулируем создание данных как в коде
    from datetime import datetime
    import time
    
    creation_datetime = datetime.now().strftime('%d.%m.%Y %H:%M')
    datetime_combined = f"{booking_data.get('date', '')} {booking_data.get('time', '')}"
    
    if is_admin_booking:
        channel = "Админ-панель"
        creator_name = "Нил Михайлюк"
    else:
        channel = "Гостевое бронирование"
        creator_name = "👤 Посетитель (через бота)"
    
    utm_data = {
        'utm_source': 'vk',
        'utm_medium': 'social',
        'utm_campaign': 'direct',
        'utm_content': 'vkontakte_page',
        'utm_term': 'client_booking'
    }
    
    # Формируем строку для новой таблицы (колонки A-P)
    row_data = [
        creation_datetime,                      # A: Дата Заявки
        channel,                                # B: Канал
        creator_name,                           # C: Кто создал заявку
        'Новая',                                # D: Статус
        f"BID-{int(time.time())}",              # E: ID us (ID заявки)
        booking_data.get('name', ''),           # F: Имя Гостя
        booking_data.get('phone', ''),          # G: Телефон
        datetime_combined,                      # H: Дата / Время
        booking_data.get('guests', ''),         # I: Кол-во гостей
        booking_data.get('reason', ''),         # J: Повод Визита
        utm_data.get('utm_source', ''),         # K: UTM Source (Источник)
        utm_data.get('utm_medium', ''),         # L: UTM Medium (Канал)
        utm_data.get('utm_campaign', ''),       # M: UTM Campaign (Кампания)
        utm_data.get('utm_content', ''),        # N: UTM Content (Содержание)
        utm_data.get('utm_term', ''),           # O: UTM Term (Ключ/Дата)
        user_id                                 # P: ID TG
    ]
    
    print(f"Подготовленная строка: {len(row_data)} колонок")
    print("Данные для экспорта:")
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    for i, (col, value) in enumerate(zip(columns, row_data)):
        print(f"   {col}: {value}")

if __name__ == "__main__":
    print("🚀 Тестирование второй таблицы\n")
    
    test_secondary_table_connection()
    test_data_structure()
    
    print("\n🏁 Тестирование завершено!")
