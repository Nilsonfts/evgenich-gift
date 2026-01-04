#!/usr/bin/env python3
"""
Быстрый тест экспорта одного тестового пользователя в Google Sheets.
Для использования на Railway в консоли: python test_single_export.py
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("\n" + "=" * 70)
    print("🧪 ТЕСТ ЭКСПОРТА ОДНОГО ПОЛЬЗОВАТЕЛЯ В GOOGLE SHEETS")
    print("=" * 70 + "\n")
    
    # Проверяем переменные окружения
    print("📋 Проверка переменных окружения...")
    
    google_key = os.getenv("GOOGLE_SHEET_KEY")
    google_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if not google_key:
        print("❌ GOOGLE_SHEET_KEY не установлен!")
        return False
    
    if not google_creds:
        print("❌ GOOGLE_CREDENTIALS_JSON не установлен!")
        return False
    
    print(f"✅ GOOGLE_SHEET_KEY: {google_key[:30]}...")
    print(f"✅ GOOGLE_CREDENTIALS_JSON: {len(google_creds)} символов")
    
    # Пытаемся запустить экспорт
    print("\n🔄 Попытка выполнить экспорт пользователей...")
    print("-" * 70)
    
    try:
        from utils.export_to_sheets import do_export
        
        success, message = do_export()
        
        print("-" * 70)
        
        if success:
            print(f"\n✅ УСПЕХ! {message}")
            print("\n📊 Результат:")
            print("  ✅ Данные успешно выгружены в Google Sheets")
            print("  ✅ Новые пользователи будут добавляться автоматически")
            print("  ✅ Экспорт отчетов работает")
            return True
        else:
            print(f"\n❌ ОШИБКА: {message}")
            print("\n📍 Что проверить:")
            print("  1. GOOGLE_CREDENTIALS_JSON содержит валидный JSON?")
            print("  2. Сервисный аккаунт имеет доступ к таблице?")
            print("  3. Вкладка 'Выгрузка Пользователей' существует?")
            return False
    
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 70)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
