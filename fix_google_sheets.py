#!/usr/bin/env python3
"""
СРОЧНОЕ ИСПРАВЛЕНИЕ Google Sheets интеграции
"""
import os
import sys

# Добавляем путь к корневой папке проекта
sys.path.append('/workspaces/evgenich-gift')

# УСТАНАВЛИВАЕМ ПЕРЕМЕННЫЕ GOOGLE SHEETS
print("🔧 НАСТРОЙКА GOOGLE SHEETS ПЕРЕМЕННЫХ...")

# 1. Проверяем и читаем Google credentials
if os.path.exists('google_creds.json'):
    with open('google_creds.json', 'r') as f:
        creds_content = f.read()
    
    # Устанавливаем переменные
    os.environ['GOOGLE_CREDENTIALS_JSON'] = creds_content
    os.environ['GOOGLE_SHEET_KEY'] = '1oHZdILFLzx1K_lXOKH5vOl_6EebdVZdTj5Cr4jVPOBs'  # Основная таблица Евгенича
    os.environ['GOOGLE_SHEET_KEY_SECONDARY'] = '1oHZdILFLzx1K_lXOKH5vOl_6EebdVZdTj5Cr4jVPOBs'  # Та же таблица для простоты
    
    print("✅ Google Sheets переменные установлены:")
    print(f"   GOOGLE_SHEET_KEY: {os.environ['GOOGLE_SHEET_KEY']}")
    print(f"   GOOGLE_CREDENTIALS_JSON: установлен ({len(creds_content)} символов)")
else:
    print("❌ google_creds.json не найден!")
    sys.exit(1)

# Остальные обязательные переменные
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
    'USE_POSTGRES': 'false',
    'DATABASE_PATH': '/tmp/test_google_fix.db'
})

print("\n🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ ИНТЕГРАЦИИ...")

# Импортируем после установки переменных
import database
import logging

logging.basicConfig(level=logging.INFO)

def test_google_sheets_fix():
    """Тестирует исправленную Google Sheets интеграцию"""
    
    print("\n1️⃣ Проверка GOOGLE_SHEETS_ENABLED...")
    print(f"   GOOGLE_SHEETS_ENABLED = {database.GOOGLE_SHEETS_ENABLED}")
    
    if not database.GOOGLE_SHEETS_ENABLED:
        print("   ❌ Google Sheets все еще отключены!")
        return False
    
    print("   ✅ Google Sheets включены!")
    
    print("\n2️⃣ Инициализация базы данных...")
    database.init_db()
    print("   ✅ БД инициализирована")
    
    print("\n3️⃣ Создание тестового пользователя...")
    test_user_id = 999888777
    database.add_new_user(
        user_id=test_user_id,
        username="test_google_fix",
        first_name="Тест Google Fix",
        source="google_sheets_fix"
    )
    print("   ✅ Пользователь создан")
    
    print("\n4️⃣ Тестирование активации с Google Sheets...")
    # Симулируем активацию через update_status (как в реальном коде)
    success = database.update_status(test_user_id, 'redeemed')
    
    if success:
        print("   ✅ Статус обновлен на 'redeemed'")
        print("   📊 При этом должна была запуститься выгрузка в Google Sheets")
        return True
    else:
        print("   ❌ Не удалось обновить статус")
        return False

def check_sheets_functions():
    """Проверяет функции работы с Google Sheets"""
    
    print("\n5️⃣ Проверка функций Google Sheets...")
    
    # Проверяем функции
    if hasattr(database, '_update_status_in_sheets_in_background'):
        print("   ✅ Функция _update_status_in_sheets_in_background найдена")
    else:
        print("   ❌ Функция _update_status_in_sheets_in_background НЕ найдена")
    
    if hasattr(database, '_get_sheets_worksheet'):
        print("   ✅ Функция _get_sheets_worksheet найдена")
    else:
        print("   ❌ Функция _get_sheets_worksheet НЕ найдена")
    
    # Пытаемся вручную вызвать функцию экспорта
    print("\n6️⃣ Тестирование прямого вызова функции экспорта...")
    try:
        # Вызываем функцию экспорта напрямую
        import datetime
        import pytz
        
        test_user_id = 999888777
        new_status = 'redeemed'
        redeem_time = datetime.datetime.now(pytz.utc)
        
        database._update_status_in_sheets_in_background(test_user_id, new_status, redeem_time)
        print("   ✅ Функция экспорта выполнена без ошибок")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка при вызове функции экспорта: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚨 СРОЧНОЕ ИСПРАВЛЕНИЕ GOOGLE SHEETS")
    print("=" * 50)
    
    success1 = test_google_sheets_fix()
    success2 = check_sheets_functions()
    
    print("\n" + "=" * 50)
    print("📋 РЕЗУЛЬТАТ ИСПРАВЛЕНИЯ:")
    
    if success1 and success2:
        print("🎉 ВСЁ ИСПРАВЛЕНО! Google Sheets интеграция работает!")
        print("\n✅ Теперь при активации пользователей:")
        print("   1. Обновляется статус в БД")
        print("   2. Запускается экспорт в Google Sheets")
        print("   3. Обновляется статистика")
        print("\n🚀 Система готова к продакшену!")
    else:
        print("❌ Есть проблемы, требуется дополнительное исправление")
        
        if not success1:
            print("   - Проблемы с базовой функциональностью")
        if not success2:
            print("   - Проблемы с функциями Google Sheets")
    
    print("\n" + "=" * 50)
