#!/usr/bin/env python3
"""
Исправляем Google Sheets - создаем правильную таблицу
"""
import os
import sys
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# Настраиваем credentials
def setup_google_sheets():
    """Настраиваем подключение к Google Sheets"""
    
    print("🔧 Настройка Google Sheets...")
    
    # Читаем credentials из файла
    if os.path.exists('google_creds.json'):
        creds = Credentials.from_service_account_file(
            'google_creds.json',
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        
        client = gspread.authorize(creds)
        print("✅ Подключение к Google Sheets установлено")
        return client
    else:
        print("❌ Файл google_creds.json не найден!")
        return None

def find_or_create_sheet(client):
    """Находит или создает Google таблицу для Евгенича"""
    
    print("\n📊 Поиск/создание Google таблицы...")
    
    # Сначала пытаемся найти существующие таблицы
    try:
        spreadsheets = client.list_spreadsheet_files()
        print(f"📋 Найдено {len(spreadsheets)} таблиц в аккаунте")
        
        # Ищем таблицу Евгенича
        evgenich_sheets = [s for s in spreadsheets if 'евгенич' in s['name'].lower() or 'evgenich' in s['name'].lower()]
        
        if evgenich_sheets:
            print(f"🎯 Найдены таблицы Евгенича:")
            for sheet in evgenich_sheets:
                print(f"   - {sheet['name']} (ID: {sheet['id']})")
            
            # Используем первую найденную
            sheet_id = evgenich_sheets[0]['id']
            sheet_name = evgenich_sheets[0]['name']
            
            try:
                spreadsheet = client.open_by_key(sheet_id)
                print(f"✅ Подключились к таблице: {sheet_name}")
                return spreadsheet, sheet_id
            except Exception as e:
                print(f"❌ Не удалось открыть таблицу {sheet_name}: {e}")
        
        print("📝 Создаю новую таблицу...")
        
    except Exception as e:
        print(f"⚠️ Не удалось получить список таблиц: {e}")
        print("📝 Создаю новую таблицу...")
    
    # Создаем новую таблицу
    try:
        spreadsheet = client.create("Евгенич - Пользователи")
        sheet_id = spreadsheet.id
        
        # Делаем таблицу публичной для чтения
        spreadsheet.share('', perm_type='anyone', role='reader')
        print(f"✅ Создана новая таблица: ID = {sheet_id}")
        
        return spreadsheet, sheet_id
        
    except Exception as e:
        print(f"❌ Не удалось создать таблицу: {e}")
        return None, None

def setup_worksheet(spreadsheet):
    """Настраиваем лист в таблице"""
    
    print("\n📄 Настройка рабочего листа...")
    
    try:
        # Получаем или создаем лист "Выгрузка Пользователей"
        try:
            worksheet = spreadsheet.worksheet("Выгрузка Пользователей")
            print("✅ Лист 'Выгрузка Пользователей' найден")
        except:
            worksheet = spreadsheet.add_worksheet(title="Выгрузка Пользователей", rows=1000, cols=10)
            print("✅ Создан лист 'Выгрузка Пользователей'")
        
        # Настраиваем заголовки
        headers = [
            'Дата', 'Время', 'User ID', 'Username', 'Имя', 'Фамилия', 
            'Статус', 'Источник', 'Дата активации', 'Реферер'
        ]
        
        # Проверяем первую строку
        first_row = worksheet.row_values(1)
        if not first_row or first_row != headers:
            worksheet.update('A1:J1', [headers])
            print("✅ Заголовки установлены")
        else:
            print("✅ Заголовки уже настроены")
        
        return worksheet
        
    except Exception as e:
        print(f"❌ Ошибка настройки листа: {e}")
        return None

def test_sheet_integration(worksheet, sheet_id):
    """Тестирует работу с таблицей"""
    
    print("\n🧪 Тестирование записи в таблицу...")
    
    try:
        # Добавляем тестовую запись
        test_data = [
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%H:%M:%S'), 
            '999999999',
            'test_user',
            'Тест',
            'Пользователь',
            'redeemed',
            'google_sheets_test',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ''
        ]
        
        # Находим следующую пустую строку
        values = worksheet.get_all_values()
        next_row = len(values) + 1
        
        # Записываем тестовые данные
        worksheet.update(f'A{next_row}:J{next_row}', [test_data])
        
        print(f"✅ Тестовая запись добавлена в строку {next_row}")
        print(f"📊 Данные: {test_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка записи в таблицу: {e}")
        return False

def main():
    """Основная функция исправления"""
    
    print("🚨 ИСПРАВЛЕНИЕ GOOGLE SHEETS ИНТЕГРАЦИИ")
    print("=" * 50)
    
    # 1. Подключение к Google Sheets
    client = setup_google_sheets()
    if not client:
        print("❌ Не удалось подключиться к Google Sheets")
        return False
    
    # 2. Поиск/создание таблицы
    spreadsheet, sheet_id = find_or_create_sheet(client)
    if not spreadsheet:
        print("❌ Не удалось найти/создать таблицу")
        return False
    
    # 3. Настройка листа
    worksheet = setup_worksheet(spreadsheet)
    if not worksheet:
        print("❌ Не удалось настроить рабочий лист")
        return False
    
    # 4. Тестирование
    test_success = test_sheet_integration(worksheet, sheet_id)
    
    # 5. Результаты
    print("\n" + "=" * 50)
    print("📋 РЕЗУЛЬТАТЫ ИСПРАВЛЕНИЯ:")
    
    if test_success:
        print("🎉 GOOGLE SHEETS ПОЛНОСТЬЮ ИСПРАВЛЕН!")
        print(f"\n✅ Таблица готова:")
        print(f"   📊 Название: {spreadsheet.title}")
        print(f"   🆔 ID: {sheet_id}")
        print(f"   🔗 URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
        print(f"\n🔧 Обновите конфигурацию:")
        print(f"   GOOGLE_SHEET_KEY={sheet_id}")
        print(f"\n✅ Теперь активации пользователей будут автоматически")
        print(f"   записываться в Google таблицу!")
        
        # Создаем исправленный .env файл
        env_content = f"""# ИСПРАВЛЕННАЯ КОНФИГУРАЦИЯ GOOGLE SHEETS
GOOGLE_SHEET_KEY={sheet_id}
GOOGLE_CREDENTIALS_JSON=$(cat google_creds.json)

# Другие переменные...
# (добавьте остальные переменные из .env.example)
"""
        with open('.env.fixed', 'w') as f:
            f.write(env_content)
        print(f"\n📄 Создан файл .env.fixed с правильной конфигурацией")
        
    else:
        print("❌ Есть проблемы с Google Sheets")
    
    print("\n" + "=" * 50)
    return test_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
