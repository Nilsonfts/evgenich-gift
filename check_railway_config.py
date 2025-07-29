#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки настроек второй таблицы на Railway.
Этот скрипт нужно запустить на производственном сервере.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def check_railway_config():
    """Проверяет конфигурацию Railway для второй таблицы."""
    
    print("🚂 ПРОВЕРКА КОНФИГУРАЦИИ RAILWAY")
    print("=" * 50)
    
    # Проверяем основные переменные
    env_vars = [
        'BOT_TOKEN',
        'GOOGLE_SHEET_KEY',
        'GOOGLE_CREDENTIALS_JSON',
        'CHANNEL_ID',
        'ADMIN_IDS'
    ]
    
    print("🔍 Проверка переменных окружения:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_CREDENTIALS_JSON':
                print(f"  ✅ {var}: JSON установлен ({len(value)} символов)")
            elif var == 'GOOGLE_SHEET_KEY':
                # Проверяем количество ключей
                keys = [k.strip() for k in value.split(',') if k.strip()]
                print(f"  ✅ {var}: {len(keys)} ключ(а)")
                for i, key in enumerate(keys):
                    print(f"     {i+1}. {key[:10]}...{key[-10:]}")
            else:
                print(f"  ✅ {var}: установлен")
        else:
            print(f"  ❌ {var}: НЕ установлен")
    
    print()
    
    # Анализ ключей Google Sheets
    google_sheet_key_raw = os.getenv("GOOGLE_SHEET_KEY")
    if google_sheet_key_raw:
        keys = [key.strip() for key in google_sheet_key_raw.split(',') if key.strip()]
        
        print(f"📊 АНАЛИЗ GOOGLE SHEETS КЛЮЧЕЙ:")
        print(f"   Всего ключей: {len(keys)}")
        
        if len(keys) >= 1:
            print(f"   🗝️ Основная таблица: {keys[0][:15]}...")
            
        if len(keys) >= 2:
            print(f"   🗝️ Дополнительная таблица: {keys[1][:15]}...")
            print("   ✅ Вторая таблица НАСТРОЕНА")
        else:
            print("   ❌ Вторая таблица НЕ НАСТРОЕНА")
            print("   🔧 Нужно добавить второй ключ через запятую в GOOGLE_SHEET_KEY")
        
        print()
    
    # Проверяем доступ к Google Sheets API
    google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if google_credentials_json and google_sheet_key_raw:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            print("🔌 ТЕСТ ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS:")
            
            # Подключение
            credentials_info = json.loads(google_credentials_json)
            credentials = Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            gc = gspread.authorize(credentials)
            keys = [key.strip() for key in google_sheet_key_raw.split(',') if key.strip()]
            
            # Тест основной таблицы
            try:
                main_sheet = gc.open_by_key(keys[0])
                print(f"   ✅ Основная таблица: '{main_sheet.title}'")
            except Exception as e:
                print(f"   ❌ Основная таблица: {e}")
            
            # Тест дополнительной таблицы
            if len(keys) >= 2:
                try:
                    secondary_sheet = gc.open_by_key(keys[1])
                    print(f"   ✅ Дополнительная таблица: '{secondary_sheet.title}'")
                    
                    # Проверяем нужную вкладку
                    target_gid = "871899838"
                    target_ws = None
                    
                    print(f"   🔍 Поиск вкладки с ID {target_gid}:")
                    for ws in secondary_sheet.worksheets():
                        print(f"      - {ws.title} (id={ws.id})")
                        if str(ws.id) == target_gid:
                            target_ws = ws
                    
                    if target_ws:
                        print(f"   ✅ Целевая вкладка найдена: '{target_ws.title}'")
                        try:
                            headers = target_ws.row_values(1)
                            print(f"   📋 Заголовки ({len(headers)} колонок): {headers[:5]}...")
                        except:
                            print("   ⚠️ Не удалось получить заголовки")
                    else:
                        print(f"   ❌ Вкладка с ID {target_gid} НЕ НАЙДЕНА!")
                        
                except Exception as e:
                    print(f"   ❌ Дополнительная таблица: {e}")
            
        except ImportError:
            print("   ⚠️ gspread не установлен - пропускаем тест подключения")
        except Exception as e:
            print(f"   ❌ Ошибка тестирования: {e}")
    
    print()
    print("🎯 РЕКОМЕНДАЦИИ:")
    
    if not google_sheet_key_raw:
        print("   1. Установить GOOGLE_SHEET_KEY в Railway")
    elif len([k.strip() for k in google_sheet_key_raw.split(',') if k.strip()]) < 2:
        print("   1. Добавить второй ключ в GOOGLE_SHEET_KEY через запятую")
        print("      Формат: ключ_основной_таблицы,ключ_дополнительной_таблицы")
    else:
        print("   ✅ Конфигурация выглядит правильной!")

if __name__ == "__main__":
    check_railway_config()
    
    # Дополнительная информация о запуске
    print()
    print("📝 ИНСТРУКЦИЯ ДЛЯ RAILWAY:")
    print("   1. Зайти в Railway Dashboard")
    print("   2. Выбрать проект evgenich-gift")
    print("   3. Зайти в Variables")  
    print("   4. Найти GOOGLE_SHEET_KEY")
    print("   5. Убедиться что там ДВА ключа через запятую")
    print("   6. Формат: ключ1,ключ2")
    print("   7. Если второго ключа нет - добавить его")
