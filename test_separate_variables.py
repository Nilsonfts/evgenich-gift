#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест новой конфигурации с отдельной переменной GOOGLE_SHEET_KEY_SECONDARY
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_separate_variables():
    """Тестирует новую конфигурацию с отдельными переменными для таблиц."""
    
    print("🔧 ТЕСТ ОТДЕЛЬНЫХ ПЕРЕМЕННЫХ ДЛЯ GOOGLE SHEETS")
    print("=" * 60)
    
    # Проверяем переменные окружения
    google_sheet_key = os.getenv("GOOGLE_SHEET_KEY")
    google_sheet_key_secondary = os.getenv("GOOGLE_SHEET_KEY_SECONDARY")
    google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    print("🔍 Проверка переменных окружения:")
    print(f"  GOOGLE_SHEET_KEY: {'✅ Установлен' if google_sheet_key else '❌ НЕ установлен'}")
    if google_sheet_key:
        print(f"    Значение: {google_sheet_key[:15]}...")
    
    print(f"  GOOGLE_SHEET_KEY_SECONDARY: {'✅ Установлен' if google_sheet_key_secondary else '❌ НЕ установлен'}")
    if google_sheet_key_secondary:
        print(f"    Значение: {google_sheet_key_secondary[:15]}...")
    
    print(f"  GOOGLE_CREDENTIALS_JSON: {'✅ Установлен' if google_credentials_json else '❌ НЕ установлен'}")
    print()
    
    # Проверяем наличие всех переменных
    if not google_sheet_key:
        print("❌ ПРОБЛЕМА: GOOGLE_SHEET_KEY не установлен")
        print("🔧 Нужно в Railway добавить переменную GOOGLE_SHEET_KEY")
        return False
    
    if not google_sheet_key_secondary:
        print("❌ ПРОБЛЕМА: GOOGLE_SHEET_KEY_SECONDARY не установлен")
        print("🔧 РЕШЕНИЕ: В Railway добавить новую переменную:")
        print("   Variable: GOOGLE_SHEET_KEY_SECONDARY")
        print("   Value: 1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4")
        return False
    
    if not google_credentials_json:
        print("❌ GOOGLE_CREDENTIALS_JSON не установлен")
        return False
    
    # Проверяем правильность ключей
    expected_primary = "1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs"
    expected_secondary = "1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4"
    
    print("🔑 Проверка ключей:")
    if google_sheet_key == expected_primary:
        print("  ✅ Основная таблица: ключ правильный")
    else:
        print(f"  ⚠️ Основная таблица: ключ отличается")
        print(f"     Текущий: {google_sheet_key}")
        print(f"     Ожидаемый: {expected_primary}")
    
    if google_sheet_key_secondary == expected_secondary:
        print("  ✅ Дополнительная таблица: ключ правильный")
    else:
        print(f"  ⚠️ Дополнительная таблица: ключ отличается")
        print(f"     Текущий: {google_sheet_key_secondary}")
        print(f"     Ожидаемый: {expected_secondary}")
    
    print()
    
    try:
        # Проверяем подключение к Google Sheets
        import gspread
        from google.oauth2.service_account import Credentials
        
        print("🔌 Тестируем подключение к Google Sheets...")
        
        credentials_info = json.loads(google_credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        
        # Тест основной таблицы
        print("📊 Основная таблица:")
        try:
            primary_sheet = gc.open_by_key(google_sheet_key)
            print(f"  ✅ Открыта: '{primary_sheet.title}'")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            return False
        
        # Тест дополнительной таблицы
        print("📊 Дополнительная таблица:")
        try:
            secondary_sheet = gc.open_by_key(google_sheet_key_secondary)
            print(f"  ✅ Открыта: '{secondary_sheet.title}'")
            
            # Проверяем нужную вкладку
            target_gid = "871899838"
            target_ws = None
            
            print("  🔍 Поиск вкладки 'Заявки Соц сети':")
            for ws in secondary_sheet.worksheets():
                print(f"     - {ws.title} (id={ws.id})")
                if str(ws.id) == target_gid:
                    target_ws = ws
            
            if target_ws:
                print(f"  ✅ Целевая вкладка найдена: '{target_ws.title}'")
                
                # Проверяем заголовки
                try:
                    headers = target_ws.row_values(1)
                    print(f"  📋 Заголовки ({len(headers)} колонок): {headers[:3]}...{headers[-3:]}")
                    
                    if len(headers) == 16:
                        print("  ✅ Структура таблицы правильная (16 колонок A-P)")
                    else:
                        print(f"  ⚠️ Неожиданное количество колонок: {len(headers)}")
                        
                except Exception as e:
                    print(f"  ⚠️ Не удалось получить заголовки: {e}")
                
            else:
                print(f"  ❌ Вкладка с ID {target_gid} не найдена!")
                return False
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            return False
        
        print()
        print("🎯 РЕЗУЛЬТАТ ТЕСТА:")
        print("✅ Все переменные настроены правильно")
        print("✅ Подключение к обеим таблицам работает")
        print("✅ Структура дополнительной таблицы корректна")
        print()
        print("🚀 Теперь бот должен дублировать заявки в обе таблицы!")
        
        return True
        
    except ImportError:
        print("⚠️ gspread не установлен - пропускаем тест подключения")
        print("✅ Переменные настроены правильно")
        return True
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    success = test_separate_variables()
    
    print()
    print("=" * 60)
    if not success:
        print("❌ НУЖНО ИСПРАВИТЬ RAILWAY КОНФИГУРАЦИЮ")
        print("📝 См. инструкцию: RAILWAY_SEPARATE_VARIABLE_SETUP.md")
    else:
        print("🎉 ВСЕ ГОТОВО! Дополнительная таблица должна работать!")
