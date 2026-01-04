#!/usr/bin/env python3
"""
Скрипт для диагностики и проверки подключения к Google Sheets и экспорта пользователей.
Используйте на Railway в raw editor mode, чтобы убедиться что всё работает.
"""

import os
import sys
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TestSheetsIntegration")

def test_environment_variables():
    """Проверяет переменные окружения."""
    logger.info("=" * 60)
    logger.info("ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    logger.info("=" * 60)
    
    vars_to_check = [
        "BOT_TOKEN",
        "GOOGLE_SHEET_KEY",
        "GOOGLE_CREDENTIALS_JSON",
        "DATABASE_PATH",
        "USE_POSTGRES",
        "DATABASE_URL"
    ]
    
    for var in vars_to_check:
        value = os.getenv(var)
        if var == "BOT_TOKEN":
            display_value = f"{'***' + value[-10:] if value else 'NOT SET'}"
        elif var == "GOOGLE_CREDENTIALS_JSON":
            if value:
                display_value = f"(JSON, {len(value)} chars)"
            else:
                display_value = "NOT SET"
        else:
            display_value = value or "NOT SET"
        
        logger.info(f"{var}: {display_value}")

def test_config_loading():
    """Проверяет загрузку конфига."""
    logger.info("\n" + "=" * 60)
    logger.info("ПРОВЕРКА ЗАГРУЗКИ КОНФИГА")
    logger.info("=" * 60)
    
    try:
        from core.config import (
            GOOGLE_SHEET_KEY, 
            GOOGLE_CREDENTIALS_JSON, 
            DATABASE_PATH,
            USE_POSTGRES,
            DATABASE_URL
        )
        
        logger.info(f"✅ GOOGLE_SHEET_KEY loaded: {bool(GOOGLE_SHEET_KEY)}")
        logger.info(f"✅ GOOGLE_CREDENTIALS_JSON loaded: {bool(GOOGLE_CREDENTIALS_JSON)}")
        logger.info(f"✅ DATABASE_PATH: {DATABASE_PATH}")
        logger.info(f"✅ USE_POSTGRES: {USE_POSTGRES}")
        logger.info(f"✅ DATABASE_URL: {'set' if DATABASE_URL else 'not set'}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error loading config: {e}")
        return False

def test_credentials_json_parsing():
    """Проверяет парсинг JSON credentials."""
    logger.info("\n" + "=" * 60)
    logger.info("ПРОВЕРКА ПАРСИНГА CREDENTIALS JSON")
    logger.info("=" * 60)
    
    try:
        from core.config import _parse_json_safe, GOOGLE_CREDENTIALS_JSON
        
        if not GOOGLE_CREDENTIALS_JSON:
            logger.warning("⚠️  GOOGLE_CREDENTIALS_JSON не установлен")
            return False
        
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        
        # Проверяем ключевые поля
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        missing_fields = [f for f in required_fields if f not in creds_dict]
        
        if missing_fields:
            logger.error(f"❌ Missing fields in credentials: {missing_fields}")
            return False
        
        logger.info(f"✅ Credentials JSON parsed successfully")
        logger.info(f"   - Type: {creds_dict.get('type')}")
        logger.info(f"   - Project ID: {creds_dict.get('project_id')}")
        logger.info(f"   - Client Email: {creds_dict.get('client_email')}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error parsing credentials JSON: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_google_sheets_connection():
    """Проверяет подключение к Google Sheets."""
    logger.info("\n" + "=" * 60)
    logger.info("ПРОВЕРКА ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS")
    logger.info("=" * 60)
    
    try:
        from core.config import GOOGLE_SHEET_KEY, GOOGLE_CREDENTIALS_JSON
        import gspread
        from google.oauth2.service_account import Credentials
        
        if not GOOGLE_SHEET_KEY:
            logger.warning("⚠️  GOOGLE_SHEET_KEY не установлен")
            return False
        
        if not GOOGLE_CREDENTIALS_JSON:
            logger.warning("⚠️  GOOGLE_CREDENTIALS_JSON не установлен")
            return False
        
        # Парсим credentials
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Авторизуемся
        gc = gspread.authorize(creds)
        logger.info("✅ Successfully authorized with Google")
        
        # Открываем таблицу
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        logger.info(f"✅ Opened spreadsheet: {spreadsheet.title}")
        
        # Список всех вкладок
        logger.info("📋 Available worksheets:")
        for ws in spreadsheet.worksheets():
            logger.info(f"   - {ws.title} (id={ws.id}, rows={ws.row_count}, cols={ws.col_count})")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error connecting to Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_database_connection():
    """Проверяет подключение к базе данных."""
    logger.info("\n" + "=" * 60)
    logger.info("ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
    logger.info("=" * 60)
    
    try:
        from core.config import USE_POSTGRES, DATABASE_PATH
        
        if USE_POSTGRES:
            logger.info("🔄 PostgreSQL mode enabled, skipping SQLite check")
            logger.info("Note: PostgreSQL connection is handled separately by the bot")
        else:
            import sqlite3
            
            # Проверяем SQLite
            try:
                conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=5)
                cursor = conn.cursor()
                
                # Простой тест - получить список таблиц
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                conn.close()
                
                logger.info(f"✅ SQLite connection successful: {DATABASE_PATH}")
                logger.info(f"   - Tables: {len(tables)}")
                for table in tables:
                    logger.info(f"     * {table[0]}")
                
                return True
            except Exception as e:
                logger.error(f"❌ SQLite connection error: {e}")
                return False
    except Exception as e:
        logger.error(f"❌ Error checking database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_export_function():
    """Тестирует функцию экспорта."""
    logger.info("\n" + "=" * 60)
    logger.info("ПРОВЕРКА ФУНКЦИИ ЭКСПОРТА")
    logger.info("=" * 60)
    
    try:
        from utils.export_to_sheets import do_export
        
        logger.info("Attempting to run export...")
        success, message = do_export()
        
        if success:
            logger.info(f"✅ Export successful: {message}")
        else:
            logger.error(f"❌ Export failed: {message}")
        
        return success
    except Exception as e:
        logger.error(f"❌ Error running export: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Главная функция проверки."""
    logger.info("\n" + "🔍 ДИАГНОСТИКА СИСТЕМЫ GOOGLE SHEETS".center(60) + "\n")
    
    results = {
        "Environment Variables": test_environment_variables(),
        "Config Loading": test_config_loading(),
        "Credentials JSON Parsing": test_credentials_json_parsing(),
        "Google Sheets Connection": test_google_sheets_connection(),
        "Database Connection": test_database_connection(),
        "Export Function": test_export_function(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("ИТОГОВЫЙ ОТЧЁТ")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info("=" * 60 + "\n")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Система готова к работе.")
        sys.exit(0)
    else:
        logger.warning("⚠️  НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ. Смотрите выше для деталей.")
        sys.exit(1)

if __name__ == "__main__":
    main()
