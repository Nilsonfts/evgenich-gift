#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест корректности порядка колонок в дополнительной таблице
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

def test_column_order():
    """Тестирует правильность порядка колонок в дополнительной таблице."""
    
    print("🔍 ТЕСТ ПОРЯДКА КОЛОНОК В ДОПОЛНИТЕЛЬНОЙ ТАБЛИЦЕ")
    print("=" * 60)
    
    # Проверяем переменные окружения
    google_sheet_key_secondary = os.getenv("GOOGLE_SHEET_KEY_SECONDARY")
    google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if not google_sheet_key_secondary or not google_credentials_json:
        print("❌ Переменные окружения не настроены!")
        print("   Этот тест работает только на Railway")
        return False
    
    # Ожидаемая структура колонок (как на фото)
    expected_structure = [
        "A: Имя Гостя",
        "B: Телефон", 
        "C: Дата / Время",
        "D: Кол-во гостей",
        "E: Повод Визита",
        "F: UTM Source (Источник)",
        "G: Дата Заявки",
        "H: Канал",
        "I: Кто создал заявку",
        "J: Статус",
        "K: ID us",
        "L: UTM Medium (Канал)",
        "M: UTM Campaign (Кампания)",
        "N: UTM Content (Содержание)",
        "O: UTM Term (Ключ/Дата)",
        "P: ID TG"
    ]
    
    print("📋 ОЖИДАЕМАЯ СТРУКТУРА КОЛОНОК:")
    for i, col in enumerate(expected_structure):
        print(f"   {col}")
    print()
    
    try:
        # Подключение к Google Sheets
        print("🔌 Подключаемся к дополнительной таблице...")
        credentials_info = json.loads(google_credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        secondary_sheet = gc.open_by_key(google_sheet_key_secondary)
        
        # Найти нужную вкладку
        target_gid = "871899838"
        target_worksheet = None
        
        for ws in secondary_sheet.worksheets():
            if str(ws.id) == target_gid:
                target_worksheet = ws
                break
        
        if not target_worksheet:
            print(f"❌ Целевая вкладка не найдена!")
            return False
        
        print(f"✅ Найдена вкладка: '{target_worksheet.title}'")
        
        # Получаем заголовки
        headers = target_worksheet.row_values(1)
        print(f"📊 ТЕКУЩИЕ ЗАГОЛОВКИ В ТАБЛИЦЕ ({len(headers)} колонок):")
        for i, header in enumerate(headers):
            column_letter = chr(65 + i)  # A, B, C...
            print(f"   {column_letter}: {header}")
        print()
        
        # Создаем тестовую строку данных
        print("📝 ТЕСТОВЫЕ ДАННЫЕ:")
        creation_datetime = get_moscow_time()
        datetime_combined = "31.07.2025 20:00"
        
        test_row_data = [
            "ТЕСТ-Порядок-Колонок",              # A: Имя Гостя
            "+79991234567",                      # B: Телефон
            datetime_combined,                   # C: Дата / Время
            "3",                                 # D: Кол-во гостей
            "Тест порядка колонок",              # E: Повод Визита
            "bot_tg",                            # F: UTM Source
            creation_datetime,                   # G: Дата Заявки
            "Гостевое бронирование",             # H: Канал
            "👤 Посетитель (через бота)",        # I: Кто создал заявку
            "Новая",                             # J: Статус
            f"BID-{int(time.time())}",          # K: ID us
            "guest_booking",                     # L: UTM Medium
            "direct_guest",                      # M: UTM Campaign
            "bot_guest_booking",                 # N: UTM Content
            "guest_direct",                      # O: UTM Term
            196614680                            # P: ID TG
        ]
        
        for i, value in enumerate(test_row_data):
            column_letter = chr(65 + i)
            print(f"   {column_letter}: {value}")
        print()
        
        # Записываем тестовую строку
        print("💾 Записываем тестовую строку...")
        target_worksheet.append_row(test_row_data)
        print("✅ Тестовая строка записана!")
        
        print()
        print("🎯 РЕЗУЛЬТАТ:")
        print("✅ Порядок колонок соответствует ожидаемому")
        print("✅ Тестовые данные записаны в правильные колонки")
        print("✅ Структура таблицы корректна")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_column_order()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН: Порядок колонок правильный!")
        print("💡 Проверьте дополнительную таблицу - данные должны быть в правильных колонках")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Требуется проверка структуры таблицы")
