#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест создания гостевой заявки для проверки экспорта во вторую таблицу
"""

import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime
import time
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_moscow_time():
    """Получить текущее московское время (UTC+3)."""
    try:
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        return moscow_time.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        logging.warning(f"Ошибка при получении московского времени: {e}")
        # Fallback - просто добавляем 3 часа к UTC
        moscow_time = datetime.utcnow() + timedelta(hours=3)
        return moscow_time.strftime('%d.%m.%Y %H:%M')

def parse_booking_date(date_str):
    """Простой парсер дат для теста."""
    if date_str.lower() == 'завтра':
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.strftime('%d.%m.%Y')
    return date_str

def test_guest_booking_with_secondary_export():
    """Тестирует создание гостевой заявки с экспортом во вторую таблицу."""
    
    print("🔍 Тест гостевой заявки с экспортом во вторую таблицу")
    print("=" * 60)
    
    # Проверяем переменные окружения
    google_sheet_key_raw = os.getenv("GOOGLE_SHEET_KEY")
    google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if not google_sheet_key_raw or not google_credentials_json:
        print("❌ Переменные окружения не настроены!")
        print("   Этот тест работает только на Railway где есть переменные окружения")
        print("   Локально для тестирования создайте .env файл")
        return False
    
    # Парсим ключи
    keys = [key.strip() for key in google_sheet_key_raw.split(',') if key.strip()]
    if len(keys) < 2:
        print("❌ Вторая таблица не настроена - нужно два ключа через запятую")
        return False
    
    primary_key = keys[0]
    secondary_key = keys[1]
    
    print(f"✅ Основная таблица: {primary_key[:10]}...")
    print(f"✅ Дополнительная таблица: {secondary_key[:10]}...")
    print()
    
    # Тестовые данные заявки
    booking_data = {
        'name': f'Тест-Экспорт-{int(time.time())}',
        'phone': '+79991234567',
        'date': 'завтра', 
        'time': '20:00',
        'guests': '3',
        'reason': 'Тестирование экспорта',
        'source': 'source_bot_tg'
    }
    
    user_id = 196614680  # Тестовый Telegram ID
    
    print("📋 Данные заявки:")
    for key, value in booking_data.items():
        print(f"   {key}: {value}")
    print(f"   user_id: {user_id}")
    print()
    
    try:
        # Подключение к Google Sheets
        print("🔌 Подключаемся к Google Sheets...")
        credentials_info = json.loads(google_credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        
        # Открываем дополнительную таблицу
        print("📊 Открываем дополнительную таблицу...")
        secondary_sheet = gc.open_by_key(secondary_key)
        print(f"✅ Таблица открыта: '{secondary_sheet.title}'")
        
        # Ищем нужную вкладку
        target_gid = "871899838"
        target_worksheet = None
        
        print(f"🔍 Ищем вкладку с ID {target_gid}...")
        for ws in secondary_sheet.worksheets():
            print(f"   - {ws.title} (id={ws.id})")
            if str(ws.id) == target_gid:
                target_worksheet = ws
        
        if not target_worksheet:
            print(f"❌ Вкладка с ID {target_gid} не найдена!")
            return False
        
        print(f"✅ Найдена вкладка: '{target_worksheet.title}'")
        
        # Подготавливаем данные для записи
        print("📝 Подготавливаем данные...")
        
        creation_datetime = get_moscow_time()
        booking_date = parse_booking_date(booking_data.get('date', ''))
        datetime_combined = f"{booking_date} {booking_data.get('time', '')}"
        
        # Формируем строку (A-P)
        row_data = [
            creation_datetime,                      # A: Дата Заявки  
            "Гостевое бронирование",               # B: Канал
            "👤 Посетитель (через бота)",          # C: Кто создал заявку
            'Новая',                               # D: Статус
            f"BID-{int(time.time())}",            # E: ID us
            booking_data.get('name', ''),          # F: Имя Гостя
            booking_data.get('phone', ''),         # G: Телефон
            datetime_combined,                     # H: Дата / Время
            booking_data.get('guests', ''),        # I: Кол-во гостей
            booking_data.get('reason', ''),        # J: Повод Визита
            'bot_tg',                              # K: UTM Source
            'guest_booking',                       # L: UTM Medium
            'direct_guest',                        # M: UTM Campaign
            'bot_guest_booking',                   # N: UTM Content
            'guest_direct',                        # O: UTM Term
            user_id                                # P: ID TG
        ]
        
        print(f"📊 Подготовлена строка из {len(row_data)} колонок:")
        for i, value in enumerate(row_data):
            column_letter = chr(65 + i)  # A, B, C...
            print(f"   {column_letter}: {value}")
        print()
        
        # Записываем в таблицу
        print("💾 Записываем данные в таблицу...")
        target_worksheet.append_row(row_data)
        print("✅ Данные успешно записаны!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Добавляем импорт timedelta для parse_booking_date
    from datetime import timedelta
    
    success = test_guest_booking_with_secondary_export()
    print()
    print("=" * 60)
    print(f"🎯 Результат: {'✅ УСПЕХ' if success else '❌ ОШИБКА'}")
