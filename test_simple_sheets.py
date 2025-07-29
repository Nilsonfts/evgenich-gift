#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой тест экспорта во вторую таблицу без config.py
"""

import os
import gspread
from google.oauth2.service_account import Credentials
import json
import logging
import time
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_google_sheets_access():
    print("🔍 Простой тест доступа к Google Sheets...")
    print()
    
    # Получаем переменные окружения
    google_sheet_key_raw = os.getenv("GOOGLE_SHEET_KEY")
    google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    print("📋 Проверка переменных окружения:")
    print(f"GOOGLE_SHEET_KEY: {'✅ Установлен' if google_sheet_key_raw else '❌ НЕ установлен'}")
    print(f"GOOGLE_CREDENTIALS_JSON: {'✅ Установлен' if google_credentials_json else '❌ НЕ установлен'}")
    
    if not google_sheet_key_raw:
        print("❌ GOOGLE_SHEET_KEY не найден в переменных окружения")
        return False
        
    if not google_credentials_json:
        print("❌ GOOGLE_CREDENTIALS_JSON не найден в переменных окружения")
        return False
    
    # Парсим ключи
    keys = [key.strip() for key in google_sheet_key_raw.split(',') if key.strip()]
    print(f"🔑 Найдено ключей: {len(keys)}")
    
    if len(keys) < 2:
        print("❌ Вторая таблица не настроена - нужно два ключа через запятую")
        return False
    
    primary_key = keys[0]
    secondary_key = keys[1]
    
    print(f"🗝️ Основная таблица: {primary_key[:10]}...")
    print(f"🗝️ Дополнительная таблица: {secondary_key[:10]}...")
    print()
    
    try:
        # Подключение к Google Sheets
        credentials_info = json.loads(google_credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        gc = gspread.authorize(credentials)
        
        # Проверяем доступ к дополнительной таблице
        print("🔌 Подключаемся к дополнительной таблице...")
        secondary_sheet = gc.open_by_key(secondary_key)
        
        print(f"✅ Дополнительная таблица открыта: {secondary_sheet.title}")
        print("📋 Доступные вкладки:")
        
        for ws in secondary_sheet.worksheets():
            print(f"  - {ws.title} (id={ws.id})")
        
        # Ищем нужную вкладку
        target_gid = "871899838"  # ID вкладки "Заявки Соц сети"
        target_worksheet = None
        
        for ws in secondary_sheet.worksheets():
            if str(ws.id) == target_gid:
                target_worksheet = ws
                break
        
        if target_worksheet:
            print(f"✅ Найдена целевая вкладка: {target_worksheet.title} (id={target_worksheet.id})")
            
            # Проверяем заголовки
            try:
                headers = target_worksheet.row_values(1)
                print(f"📊 Заголовки ({len(headers)} колонок): {headers}")
            except Exception as e:
                print(f"⚠️ Ошибка при получении заголовков: {e}")
                
            return True
        else:
            print(f"❌ Вкладка с id={target_gid} не найдена!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    result = test_google_sheets_access()
    print(f"\n{'✅ Тест пройден' if result else '❌ Тест провален'}")
