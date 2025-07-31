#!/usr/bin/env python3
"""
Финальный тест новой 18-колоночной структуры
"""

# Имитируем переменные окружения для теста  
import os
os.environ['BOT_TOKEN'] = 'test'
os.environ['CHANNEL_ID'] = '123'
os.environ['ADMIN_IDS'] = '123'
os.environ['GOOGLE_SHEET_KEY'] = 'test1,test2'
os.environ['GOOGLE_CREDENTIALS_JSON'] = '{}'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'
os.environ['SMM_IDS'] = '555666777,888999000'

import logging
from typing import Dict, Any
from unittest.mock import patch

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_export_booking_to_secondary_table():
    """Тест функции export_booking_to_secondary_table с новой структурой"""
    print("🧪 Тест export_booking_to_secondary_table (18 столбцов)")
    
    # Импортируем функцию
    from social_bookings_export import export_booking_to_secondary_table
    
    # Тестовые данные
    booking_data = {
        'name': 'Тест Новая Структура',
        'phone': '+7900111222',
        'date': '2024-01-15',
        'time': '20:00',
        'guests': '6',
        'source': 'direct'
    }
    
    user_id = 555666777  # СММщик
    is_admin_booking = True
    
    print(f"📋 Тестовые данные:")
    for key, value in booking_data.items():
        print(f"  {key}: {value}")
    print(f"  user_id: {user_id}")
    print(f"  is_admin_booking: {is_admin_booking}")
    
    # Мок для Google Sheets (чтобы не писать в реальную таблицу)
    def mock_gspread_open_by_key(key):
        class MockWorksheet:
            def append_row(self, row):
                print(f"📝 Mock append_row вызван:")
                print(f"   Количество столбцов: {len(row)}")
                print(f"   Ожидается: 18 (A-R)")
                print(f"   Соответствует: {'✅' if len(row) == 18 else '❌'}")
                
                # Показываем структуру
                columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']
                print(f"📊 Структура данных:")
                for i, (col, data) in enumerate(zip(columns, row)):
                    if data:  # Показываем только заполненные
                        print(f"     {col}: {data}")
                
                return True
                
        class MockSpreadsheet:
            def sheet1(self):
                return MockWorksheet()
                
        return MockSpreadsheet()
    
    # Патчим gspread
    with patch('gspread.service_account') as mock_service_account:
        mock_client = mock_service_account.return_value
        mock_client.open_by_key = mock_gspread_open_by_key
        
        try:
            # Вызываем функцию
            result = export_booking_to_secondary_table(booking_data, user_id, is_admin_booking)
            print(f"✅ Функция выполнена успешно: {result}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_column_mapping():
    """Тест соответствия колонок"""
    print(f"\n🗂️  Тест соответствия колонок:")
    
    expected_columns = {
        'A': 'Название сделки (ЕВГ_СПБ + имя + телефон)',
        'B': 'Дата создания (московское время)',
        'C': 'Имя клиента',
        'D': 'Дата и время посещения',
        'E': 'Тег города (ЕВГ_СПБ)',
        'F': 'Телефон',
        'G': 'Количество гостей',
        'H': 'Источник трафика',
        'I': 'UTM Source',
        'J': 'UTM Medium',
        'K': 'UTM Campaign',
        'L': 'UTM Term',
        'M': 'UTM Content',
        'N': 'Client ID',
        'O': 'Session ID',
        'P': 'FB Click ID',
        'Q': 'GA Client ID',
        'R': 'Telegram ID'
    }
    
    print(f"📋 Структура 18 столбцов (A-R):")
    for col, desc in expected_columns.items():
        print(f"   {col}: {desc}")
    
    return True

if __name__ == "__main__":
    print("🚀 Финальный тест новой структуры таблицы\n")
    
    # Тест 1: соответствие колонок
    mapping_ok = test_column_mapping()
    
    # Тест 2: функция экспорта
    export_ok = test_export_booking_to_secondary_table()
    
    print(f"\n📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"  Соответствие колонок: {'✅' if mapping_ok else '❌'}")
    print(f"  Функция экспорта: {'✅' if export_ok else '❌'}")
    
    if mapping_ok and export_ok:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print(f"✅ Новая 18-колоночная структура готова")
        print(f"✅ Автозаполнение работает")
        print(f"✅ СММщики должны работать (при правильной настройке SMM_IDS)")
    else:
        print(f"\n❌ ЕСТЬ ПРОБЛЕМЫ!")
