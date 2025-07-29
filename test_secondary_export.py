#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки экспорта во вторую Google Sheets таблицу
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from social_bookings_export import export_booking_to_secondary_table
from config import GOOGLE_SHEET_KEY, GOOGLE_SHEET_KEY_SECONDARY
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_secondary_export():
    print("🔍 Тестирование экспорта во вторую таблицу...")
    print()
    
    # Проверяем конфигурацию
    print("📋 Проверка конфигурации:")
    print(f"GOOGLE_SHEET_KEY (основная): {GOOGLE_SHEET_KEY[:10] + '...' if GOOGLE_SHEET_KEY else 'НЕ НАСТРОЕН'}")
    print(f"GOOGLE_SHEET_KEY_SECONDARY (дополнительная): {GOOGLE_SHEET_KEY_SECONDARY[:10] + '...' if GOOGLE_SHEET_KEY_SECONDARY else 'НЕ НАСТРОЕН'}")
    print()
    
    if not GOOGLE_SHEET_KEY_SECONDARY:
        print("❌ GOOGLE_SHEET_KEY_SECONDARY не настроен!")
        print("🔧 Нужно добавить второй ключ в переменную GOOGLE_SHEET_KEY через запятую")
        return
    
    # Тестовые данные
    test_booking_data = {
        'name': 'Тестовый-Клиент-8',
        'phone': '+7999123456789',
        'date': 'завтра',
        'time': '19:00',
        'guests': '4',
        'reason': 'День рождения',
        'source': 'source_bot_tg'
    }
    
    test_user_id = 196614680  # Ваш Telegram ID
    
    print("📊 Тестовые данные:")
    for key, value in test_booking_data.items():
        print(f"  {key}: {value}")
    print(f"  user_id: {test_user_id}")
    print()
    
    # Выполняем экспорт
    print("🚀 Запускаем экспорт во вторую таблицу...")
    result = export_booking_to_secondary_table(test_booking_data, test_user_id, is_admin_booking=False)
    
    if result:
        print("✅ Экспорт успешно выполнен!")
    else:
        print("❌ Экспорт завершился с ошибкой!")
    
    return result

if __name__ == "__main__":
    test_secondary_export()
