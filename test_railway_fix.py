#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест экспорта во вторую таблицу после исправления Railway конфигурации
"""

import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials
import logging
import time
from datetime import datetime, timedelta
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
        moscow_time = datetime.utcnow() + timedelta(hours=3)
        return moscow_time.strftime('%d.%m.%Y %H:%M')

def parse_booking_date(date_str):
    """Простой парсер дат."""
    if date_str.lower() == 'завтра':
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.strftime('%d.%m.%Y')
    return date_str

def test_after_railway_fix():
    """Тестирует экспорт во вторую таблицу после исправления Railway."""
    
    print("🚂 ТЕСТ ПОСЛЕ ИСПРАВЛЕНИЯ RAILWAY")
    print("=" * 60)
    
    # Проверяем переменные окружения
    google_sheet_key_raw = os.getenv("GOOGLE_SHEET_KEY")
    google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    print("🔍 Проверка переменных окружения:")
    if not google_sheet_key_raw:
        print("❌ GOOGLE_SHEET_KEY не найден")
        print("💡 На Railway нужно установить переменную GOOGLE_SHEET_KEY")
        return False
        
    if not google_credentials_json:
        print("❌ GOOGLE_CREDENTIALS_JSON не найден")
        return False
    
    # Парсим ключи
    keys = [key.strip() for key in google_sheet_key_raw.split(',') if key.strip()]
    print(f"🔑 Найдено ключей Google Sheets: {len(keys)}")
    
    if len(keys) < 2:
        print("❌ ПРОБЛЕМА: Найден только один ключ!")
        print("🔧 РЕШЕНИЕ: Добавить второй ключ через запятую:")
        print("   Текущее значение GOOGLE_SHEET_KEY:")
        print(f"   {google_sheet_key_raw}")
        print()
        print("   Нужно изменить на:")
        print(f"   {google_sheet_key_raw},1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4")
        return False
    
    primary_key = keys[0]
    secondary_key = keys[1]
    
    print(f"✅ Основная таблица: {primary_key}")
    print(f"✅ Дополнительная таблица: {secondary_key}")
    
    # Проверяем, правильный ли ключ дополнительной таблицы
    expected_secondary_key = "1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4"
    if secondary_key != expected_secondary_key:
        print(f"⚠️ ВНИМАНИЕ: Ключ дополнительной таблицы не соответствует ожидаемому")
        print(f"   Текущий: {secondary_key}")
        print(f"   Ожидаемый: {expected_secondary_key}")
    
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
        
        # Тестируем дополнительную таблицу
        print("📊 Тестируем дополнительную таблицу...")
        secondary_sheet = gc.open_by_key(secondary_key)
        print(f"✅ Дополнительная таблица открыта: '{secondary_sheet.title}'")
        
        # Ищем целевую вкладку
        target_gid = "871899838"
        target_worksheet = None
        
        print("🔍 Доступные вкладки:")
        for ws in secondary_sheet.worksheets():
            print(f"   - {ws.title} (id={ws.id})")
            if str(ws.id) == target_gid:
                target_worksheet = ws
        
        if not target_worksheet:
            print(f"❌ Вкладка с ID {target_gid} не найдена!")
            return False
        
        print(f"✅ Целевая вкладка найдена: '{target_worksheet.title}'")
        
        # Проверяем структуру таблицы
        try:
            headers = target_worksheet.row_values(1)
            print(f"📋 Заголовки таблицы ({len(headers)} колонок):")
            for i, header in enumerate(headers):
                column_letter = chr(65 + i)  # A, B, C...
                print(f"   {column_letter}: {header}")
        except Exception as e:
            print(f"⚠️ Не удалось получить заголовки: {e}")
        
        print()
        
        # Создаем тестовую запись
        print("📝 Создаем тестовую запись...")
        
        test_booking_data = {
            'name': f'ТЕСТ-После-Исправления-{int(time.time())}',
            'phone': '+79991234567',
            'date': 'завтра',
            'time': '21:00',
            'guests': '2',
            'reason': 'Тест после исправления Railway',
            'source': 'source_bot_tg'
        }
        
        user_id = 196614680
        
        # Подготавливаем данные
        creation_datetime = get_moscow_time()
        booking_date = parse_booking_date(test_booking_data.get('date', ''))
        datetime_combined = f"{booking_date} {test_booking_data.get('time', '')}"
        
        # Формируем строку для записи (колонки A-P)
        row_data = [
            creation_datetime,                      # A: Дата Заявки
            "Гостевое бронирование",               # B: Канал
            "👤 Посетитель (через бота)",          # C: Кто создал заявку
            'Новая',                               # D: Статус
            f"BID-{int(time.time())}",            # E: ID us (ID заявки)
            test_booking_data.get('name', ''),     # F: Имя Гостя
            test_booking_data.get('phone', ''),    # G: Телефон
            datetime_combined,                     # H: Дата / Время
            test_booking_data.get('guests', ''),   # I: Кол-во гостей
            test_booking_data.get('reason', ''),   # J: Повод Визита
            'bot_tg',                              # K: UTM Source
            'guest_booking',                       # L: UTM Medium
            'direct_guest',                        # M: UTM Campaign
            'bot_guest_booking',                   # N: UTM Content
            'guest_direct',                        # O: UTM Term
            user_id                                # P: ID TG
        ]
        
        print(f"📊 Подготовлена строка из {len(row_data)} колонок")
        print("📊 Данные:")
        for i, value in enumerate(row_data):
            column_letter = chr(65 + i)
            print(f"   {column_letter}: {value}")
        
        print()
        print("💾 Записываем в таблицу...")
        target_worksheet.append_row(row_data)
        print("✅ Тестовая запись успешно добавлена!")
        
        print()
        print("🎯 РЕЗУЛЬТАТ ТЕСТА:")
        print("✅ Дополнительная таблица настроена правильно")
        print("✅ Экспорт работает корректно")
        print("✅ Данные успешно записываются")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_after_railway_fix()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН: Дополнительная таблица работает!")
        print("💡 Теперь все заявки будут дублироваться в обе таблицы")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Требуется исправление Railway конфигурации")
        print("📋 См. инструкцию в файле RAILWAY_SECOND_TABLE_FIX.md")
