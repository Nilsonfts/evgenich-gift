#!/usr/bin/env python3
"""
Находим существующие Google таблицы
"""
import gspread
from google.oauth2.service_account import Credentials

def list_existing_sheets():
    """Показывает все существующие таблицы"""
    
    print("📊 ПОИСК СУЩЕСТВУЮЩИХ GOOGLE ТАБЛИЦ")
    print("=" * 40)
    
    try:
        # Подключение
        creds = Credentials.from_service_account_file(
            'google_creds.json',
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        client = gspread.authorize(creds)
        
        # Получаем все таблицы
        spreadsheets = client.list_spreadsheet_files()
        print(f"📋 Найдено {len(spreadsheets)} таблиц:")
        
        for i, sheet in enumerate(spreadsheets, 1):
            print(f"\n{i}. {sheet['name']}")
            print(f"   ID: {sheet['id']}")
            print(f"   URL: https://docs.google.com/spreadsheets/d/{sheet['id']}")
            
            # Пробуем открыть и посмотреть листы
            try:
                ss = client.open_by_key(sheet['id'])
                worksheets = ss.worksheets()
                print(f"   Листы: {[ws.title for ws in worksheets]}")
                
                # Проверяем подходящий ли лист
                suitable_sheets = [ws for ws in worksheets if any(keyword in ws.title.lower() for keyword in ['пользователи', 'users', 'выгрузка', 'данные'])]
                if suitable_sheets:
                    print(f"   ✅ ПОДХОДИТ! Лист: {suitable_sheets[0].title}")
                    
                    # Показываем содержимое
                    ws = suitable_sheets[0]
                    values = ws.get_all_values()
                    if values:
                        print(f"   📄 Строк данных: {len(values)}")
                        if len(values[0]) > 0:
                            print(f"   📋 Заголовки: {values[0][:5]}...")  # Первые 5 колонок
            
            except Exception as e:
                print(f"   ⚠️ Не удалось открыть: {e}")
        
        # Предлагаем лучший вариант
        print("\n" + "=" * 40)
        print("🎯 РЕКОМЕНДАЦИЯ:")
        
        if spreadsheets:
            # Ищем наиболее подходящую таблицу
            best_sheet = None
            for sheet in spreadsheets:
                name = sheet['name'].lower()
                if any(keyword in name for keyword in ['евгенич', 'evgenich', 'пользователи', 'users']):
                    best_sheet = sheet
                    break
            
            if not best_sheet:
                best_sheet = spreadsheets[0]  # Берем первую
            
            print(f"📊 Использовать таблицу: {best_sheet['name']}")
            print(f"🆔 ID: {best_sheet['id']}")
            print(f"\n🔧 Команда для обновления конфигурации:")
            print(f"export GOOGLE_SHEET_KEY='{best_sheet['id']}'")
            
            return best_sheet['id']
        else:
            print("❌ Таблицы не найдены")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

if __name__ == "__main__":
    sheet_id = list_existing_sheets()
    if sheet_id:
        print(f"\n✅ Готово! Используйте ID: {sheet_id}")
    else:
        print("\n❌ Не удалось найти подходящую таблицу")
