#!/usr/bin/env python3
"""
Диагностика проблемы с Google Sheets и статистикой
СРОЧНОЕ ИСПРАВЛЕНИЕ
"""
import os
import sys
import logging
from datetime import datetime
import pytz

# Добавляем путь к корневой папке проекта
sys.path.append('/workspaces/evgenich-gift')

# Устанавливаем переменные окружения для тестирования
os.environ.update({
    'BOT_TOKEN': 'test_token',
    'CHANNEL_ID': '-1001234567890',
    'ADMIN_IDS': '123456789',
    'BOSS_IDS': '123456789',
    'HELLO_STICKER_ID': 'test_hello_sticker',
    'NASTOYKA_STICKER_ID': 'test_nastoyka_sticker',
    'THANK_YOU_STICKER_ID': 'test_thank_you_sticker',
    'FRIEND_BONUS_STICKER_ID': 'test_friend_sticker',
    'MENU_URL': 'https://test-menu.com',
    'USE_POSTGRES': 'false',  # Тестируем на SQLite
    'DATABASE_PATH': '/tmp/test_reports.db',
    'LOG_LEVEL': 'DEBUG'
})

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_google_sheets_setup():
    """Проверяет настройку Google Sheets"""
    print("🔍 ПРОВЕРКА GOOGLE SHEETS SETUP")
    print("=" * 40)
    
    # 1. Проверяем переменные окружения
    print("\n1️⃣ Переменные окружения:")
    google_vars = {
        'GOOGLE_SHEET_KEY': os.getenv('GOOGLE_SHEET_KEY'),
        'GOOGLE_SHEET_KEY_SECONDARY': os.getenv('GOOGLE_SHEET_KEY_SECONDARY'), 
        'GOOGLE_CREDENTIALS_JSON': os.getenv('GOOGLE_CREDENTIALS_JSON')
    }
    
    for var, value in google_vars.items():
        if value:
            print(f"   ✅ {var} = {str(value)[:30]}...")
        else:
            print(f"   ❌ {var} = НЕ УСТАНОВЛЕНА!")
    
    # 2. Проверяем файлы
    print("\n2️⃣ Файлы:")
    files_to_check = [
        'google_creds.json',
        'credentials.json',
        'service-account-key.json'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   ✅ {file_path} ({size} bytes)")
        else:
            print(f"   ❌ {file_path} - НЕ НАЙДЕН")
    
    # 3. Проверяем импорты
    print("\n3️⃣ Импорты модулей:")
    try:
        import gspread
        print("   ✅ gspread")
    except ImportError as e:
        print(f"   ❌ gspread: {e}")
    
    try:
        from google.oauth2.service_account import Credentials
        print("   ✅ google.oauth2")
    except ImportError as e:
        print(f"   ❌ google.oauth2: {e}")
    
    return any(google_vars.values())

def check_database_functions():
    """Проверяет функции базы данных"""
    print("\n🗄️ ПРОВЕРКА ФУНКЦИЙ БАЗЫ ДАННЫХ")
    print("=" * 40)
    
    try:
        import database
        
        # Инициализация БД
        print("1️⃣ Инициализация базы данных...")
        database.init_db()
        print("   ✅ БД инициализирована")
        
        # Создание тестового пользователя
        test_user_id = 888888888
        print(f"2️⃣ Создание тестового пользователя {test_user_id}...")
        database.add_new_user(
            user_id=test_user_id,
            username="test_reports_user",
            first_name="Тест Репортов",
            source="test_reports"
        )
        print("   ✅ Пользователь создан")
        
        # Выдача купона
        test_coupon = "TESTREPORT123"
        print(f"3️⃣ Выдача купона {test_coupon}...")
        coupon_added = database.add_coupon_to_user(test_user_id, test_coupon)
        print(f"   {'✅' if coupon_added else '⚠️'} Купон выдан: {coupon_added}")
        
        # Активация пользователя
        print("4️⃣ Активация пользователя...")
        activation_result = database.activate_user(test_user_id)
        print(f"   Результат активации: {activation_result}")
        
        # Проверка статистики
        print("5️⃣ Проверка статистики...")
        stats = database.get_stats()
        if stats:
            print(f"   📊 Всего пользователей: {stats.get('total_users', 0)}")
            print(f"   📊 Активированных: {stats.get('activated_users', 0)}")
            print(f"   📊 Неактивных: {stats.get('inactive_users', 0)}")
        else:
            print("   ❌ Статистика недоступна")
        
        # Проверка получения активированных пользователей
        print("6️⃣ Проверка получения активированных пользователей...")
        try:
            recent_users = database.get_recent_activated_users(limit=5)
            if recent_users:
                print(f"   ✅ Найдено {len(recent_users)} недавних активаций")
                for user in recent_users[:3]:  # Показываем первых 3
                    print(f"      - {user.get('user_id')} (@{user.get('username', 'N/A')})")
            else:
                print("   ⚠️ Нет недавних активаций")
        except Exception as e:
            print(f"   ❌ Ошибка получения активированных: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка работы с БД: {e}")
        logging.error(f"Database error: {e}", exc_info=True)
        return False

def check_google_sheets_integration():
    """Проверяет интеграцию с Google Sheets"""
    print("\n📊 ПРОВЕРКА ИНТЕГРАЦИИ GOOGLE SHEETS")
    print("=" * 40)
    
    try:
        # Пытаемся импортировать модули экспорта
        print("1️⃣ Импорт модулей экспорта...")
        try:
            import export_to_sheets
            print("   ✅ export_to_sheets импортирован")
        except Exception as e:
            print(f"   ❌ export_to_sheets: {e}")
        
        # Проверяем функции в database.py
        print("2️⃣ Проверка функций экспорта в database.py...")
        import database
        import inspect
        
        # Ищем функции связанные с Google Sheets
        db_functions = [func for func in dir(database) if 'sheet' in func.lower() or 'google' in func.lower() or 'export' in func.lower()]
        if db_functions:
            print(f"   📋 Найдены функции: {db_functions}")
        else:
            print("   ⚠️ Функции экспорта в database.py не найдены")
        
        # Проверяем активацию пользователя - ищем вызовы Google Sheets
        print("3️⃣ Проверка кода функции activate_user...")
        if hasattr(database, 'activate_user'):
            source_code = inspect.getsource(database.activate_user)
            if 'sheet' in source_code.lower() or 'google' in source_code.lower() or 'export' in source_code.lower():
                print("   ✅ В activate_user есть обращения к Google Sheets")
            else:
                print("   ❌ В activate_user НЕТ обращений к Google Sheets!")
                print("   🔧 ЭТО МОЖЕТ БЫТЬ ПРОБЛЕМА!")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки интеграции: {e}")
        return False

def check_handlers_integration():
    """Проверяет интеграцию с обработчиками"""
    print("\n🔧 ПРОВЕРКА ОБРАБОТЧИКОВ")
    print("=" * 40)
    
    try:
        # Проверяем callback_query.py
        print("1️⃣ Проверка handlers/callback_query.py...")
        if os.path.exists('handlers/callback_query.py'):
            with open('handlers/callback_query.py', 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'redeem_coupon' in content:
                print("   ✅ Найдена функция redeem_coupon")
                
                # Проверяем есть ли вызовы Google Sheets
                if 'sheet' in content.lower() or 'google' in content.lower() or 'export' in content.lower():
                    print("   ✅ В callback_query есть обращения к Google Sheets")
                else:
                    print("   ❌ В callback_query НЕТ обращений к Google Sheets!")
            else:
                print("   ❌ Функция redeem_coupon не найдена")
        else:
            print("   ❌ Файл handlers/callback_query.py не найден")
        
        # Проверяем другие handlers
        print("2️⃣ Проверка других обработчиков...")
        handlers_files = [
            'handlers/user_commands.py',
            'handlers/users.py',
            'handlers/content.py'
        ]
        
        for handler_file in handlers_files:
            if os.path.exists(handler_file):
                with open(handler_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'activate_user' in content or 'redeem' in content:
                    print(f"   📋 {handler_file}: есть функции активации")
                    
                    if 'sheet' in content.lower() or 'google' in content.lower() or 'export' in content.lower():
                        print(f"      ✅ Есть обращения к Google Sheets")
                    else:
                        print(f"      ❌ НЕТ обращений к Google Sheets!")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки handlers: {e}")
        return False

def diagnose_and_fix():
    """Основная функция диагностики и исправления"""
    print("🚨 СРОЧНАЯ ДИАГНОСТИКА ПРОБЛЕМЫ С GOOGLE SHEETS")
    print("=" * 60)
    
    # Проверяем все компоненты
    google_sheets_ok = check_google_sheets_setup()
    database_ok = check_database_functions() 
    sheets_integration_ok = check_google_sheets_integration()
    handlers_ok = check_handlers_integration()
    
    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТ ДИАГНОСТИКИ:")
    print(f"   📊 Google Sheets setup: {'✅' if google_sheets_ok else '❌'}")
    print(f"   🗄️ База данных: {'✅' if database_ok else '❌'}")
    print(f"   🔗 Интеграция Sheets: {'✅' if sheets_integration_ok else '❌'}")
    print(f"   🔧 Handlers: {'✅' if handlers_ok else '❌'}")
    
    # Предлагаем решения
    print("\n🔧 ПЛАН ИСПРАВЛЕНИЯ:")
    
    if not google_sheets_ok:
        print("1️⃣ НАСТРОИТЬ Google Sheets:")
        print("   - Проверить переменные GOOGLE_SHEET_KEY и GOOGLE_CREDENTIALS_JSON")
        print("   - Убедиться что файл credentials существует")
    
    if not sheets_integration_ok:
        print("2️⃣ ИСПРАВИТЬ интеграцию:")
        print("   - Добавить вызов экспорта в функцию activate_user()")
        print("   - Проверить импорты модулей экспорта")
    
    if not handlers_ok:
        print("3️⃣ ОБНОВИТЬ handlers:")
        print("   - Добавить экспорт в Google Sheets после активации")
        print("   - Проверить все места где происходит погашение купонов")
    
    print("\n⚡ Сейчас начинаю исправление...")
    
    return {
        'google_sheets_ok': google_sheets_ok,
        'database_ok': database_ok,
        'sheets_integration_ok': sheets_integration_ok,
        'handlers_ok': handlers_ok
    }

if __name__ == "__main__":
    print("🚀 Запуск срочной диагностики системы отчетов...")
    result = diagnose_and_fix()
    
    if not all(result.values()):
        print("\n🚨 ОБНАРУЖЕНЫ ПРОБЛЕМЫ! Требуется исправление.")
    else:
        print("\n✅ Все компоненты работают корректно.")
    
    print("\n🏁 Диагностика завершена.")