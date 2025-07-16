#!/usr/bin/env python3
"""
🧹 АВТОМАТИЧЕСКАЯ ОЧИСТКА ПРОЕКТА
Удаляет ненужные файлы и папки для упрощения структуры проекта
"""

import os
import shutil
from pathlib import Path

def cleanup_project():
    """Удаляет ненужные файлы из проекта."""
    
    print("🧹 НАЧИНАЮ ОЧИСТКУ ПРОЕКТА")
    print("=" * 50)
    
    # Счетчики
    deleted_files = 0
    deleted_dirs = 0
    errors = []
    
    # 1. Дублирующиеся отчеты и документация
    print("\n📋 1. Удаляю отчеты и документацию...")
    reports_to_delete = [
        "CALLBACK_FIX_REPORT.md",
        "CONTACT_SYSTEM_UPDATE.md",
        "CORRECT_QR_LINKS.md", 
        "DEPLOYMENT_SUCCESS.md",
        "ERROR_HANDLING_IMPROVEMENT.md",
        "FINAL_STATUS_REPORT.md",
        "FINAL_SYSTEM_REPORT.md",
        "FIXES_DOCUMENTATION.md",
        "FIXES_REPORT.md",
        "NEW_FEATURES_DOCS.md",
        "PROFILE_COLLECTION_SUMMARY.md",
        "QR_STAFF_FIX_REPORT.md",
        "QR_SYSTEM_FINAL_REPORT.md",
        "QR_SYSTEM_FIX_REPORT.md",
        "SIMPLE_QR_SYSTEM_FINAL.md",
        "SIMPLE_QR_SYSTEM_REPORT.md",
        "TASK_COMPLETION_REPORT.md"
    ]
    
    for file in reports_to_delete:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   ✅ {file}")
                deleted_files += 1
            else:
                print(f"   ⚠️ {file} (не найден)")
        except Exception as e:
            errors.append(f"Ошибка удаления {file}: {e}")
            print(f"   ❌ {file} - ОШИБКА: {e}")
    
    # 2. Тестовые файлы
    print("\n🧪 2. Удаляю тестовые файлы...")
    test_files = [
        "test_bot_functionality.py",
        "test_callback_routing.py", 
        "test_config.py",
        "test_correct_db.py",
        "test_correct_qr.py",
        "test_fixes.py",
        "test_full_qr_process.py",
        "test_new_staff_system.py",
        "test_newsletter_buttons.py",
        "test_newsletter_system.py",
        "test_profile_collection.py",
        "test_real_qr.py",
        "test_reports_new.py",
        "test_simple_qr.py",
        "test_simple_qr_system.py",
        "test_staff_lookup.py",
        "test_staff_qr_system.py",
        "test_validation_only.py"
    ]
    
    for file in test_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   ✅ {file}")
                deleted_files += 1
            else:
                print(f"   ⚠️ {file} (не найден)")
        except Exception as e:
            errors.append(f"Ошибка удаления {file}: {e}")
            print(f"   ❌ {file} - ОШИБКА: {e}")
    
    # 3. Дублирующиеся скрипты управления персоналом
    print("\n👥 3. Удаляю дублирующиеся скрипты персонала...")
    staff_files = [
        "add_kristina_staff.py",
        "add_nil680_staff.py", 
        "manage_staff.py",
        "manage_staff_new.py",
        "simple_staff_manager.py"
    ]
    
    for file in staff_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   ✅ {file}")
                deleted_files += 1
            else:
                print(f"   ⚠️ {file} (не найден)")
        except Exception as e:
            errors.append(f"Ошибка удаления {file}: {e}")
            print(f"   ❌ {file} - ОШИБКА: {e}")
    
    # 4. Дублирующиеся QR генераторы
    print("\n🎨 4. Удаляю дублирующиеся QR генераторы...")
    qr_files = [
        "add_text_to_qr.py",
        "create_qr_with_names.py",
        "final_qr_generator.py",
        "simple_qr_generator.py",
        "simple_qr_test.py",
        "ultra_simple_qr.py",
        "create_correct_qr_codes.py"
    ]
    
    for file in qr_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   ✅ {file}")
                deleted_files += 1
            else:
                print(f"   ⚠️ {file} (не найден)")
        except Exception as e:
            errors.append(f"Ошибка удаления {file}: {e}")
            print(f"   ❌ {file} - ОШИБКА: {e}")
    
    # 5. Инициализаторы и диагностика БД
    print("\n🗄️ 5. Удаляю файлы инициализации и диагностики БД...")
    db_files = [
        "check_real_db.py",
        "create_test_db.py",
        "create_test_data.py",
        "create_test_newsletter_data.py",
        "diagnose_real_db.py",
        "diagnose_real_db_fixed.py",
        "init_correct_db.py",
        "final_system_test.py",
        "bot_database.db"  # Старая тестовая БД
    ]
    
    for file in db_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   ✅ {file}")
                deleted_files += 1
            else:
                print(f"   ⚠️ {file} (не найден)")
        except Exception as e:
            errors.append(f"Ошибка удаления {file}: {e}")
            print(f"   ❌ {file} - ОШИБКА: {e}")
    
    # 6. Дублирующиеся папки QR-кодов
    print("\n🗂️ 6. Удаляю дублирующиеся папки QR-кодов...")
    qr_dirs = [
        "branded_qr_codes",
        "final_qr_codes", 
        "qr_codes",
        "qr_with_labels",
        "qr_branded",
        "qr_codes_with_names"
    ]
    
    for dir_name in qr_dirs:
        try:
            if os.path.exists(dir_name) and os.path.isdir(dir_name):
                shutil.rmtree(dir_name)
                print(f"   ✅ {dir_name}/ (папка)")
                deleted_dirs += 1
            else:
                print(f"   ⚠️ {dir_name}/ (не найдена)")
        except Exception as e:
            errors.append(f"Ошибка удаления папки {dir_name}: {e}")
            print(f"   ❌ {dir_name}/ - ОШИБКА: {e}")
    
    # 7. Очистка кэша Python
    print("\n🧹 7. Очищаю кэш Python...")
    cache_dirs = ["__pycache__"]
    
    for dir_name in cache_dirs:
        try:
            if os.path.exists(dir_name) and os.path.isdir(dir_name):
                shutil.rmtree(dir_name)
                print(f"   ✅ {dir_name}/ (кэш)")
                deleted_dirs += 1
            else:
                print(f"   ⚠️ {dir_name}/ (не найден)")
        except Exception as e:
            errors.append(f"Ошибка очистки кэша {dir_name}: {e}")
            print(f"   ❌ {dir_name}/ - ОШИБКА: {e}")
    
    # Итоги
    print("\n" + "=" * 50)
    print("🎉 ОЧИСТКА ЗАВЕРШЕНА!")
    print(f"✅ Удалено файлов: {deleted_files}")
    print(f"✅ Удалено папок: {deleted_dirs}")
    
    if errors:
        print(f"\n⚠️ Ошибки ({len(errors)}):")
        for error in errors:
            print(f"   • {error}")
    else:
        print("\n✨ Очистка прошла без ошибок!")
    
    print("\n📁 ФИНАЛЬНАЯ СТРУКТУРА:")
    print("├── main.py                    # 🤖 Основной бот")
    print("├── config.py                  # ⚙️ Конфигурация")
    print("├── database.py                # 🗄️ База данных")
    print("├── fix_kristina.py            # 🔧 Исправление QR")
    print("├── create_final_qr_codes.py   # 📱 Генератор QR")
    print("├── staff_manager.py           # 👥 Управление персоналом")
    print("├── export_to_sheets.py        # 📊 Экспорт данных")
    print("├── handlers/                  # 📝 Обработчики бота")
    print("├── keyboards/                 # ⌨️ Клавиатуры")
    print("├── texts/                     # 📄 Тексты")
    print("├── ai/                        # 🧠 AI функции")
    print("├── db/                        # 🗃️ Утилиты БД")
    print("├── data/                      # 💾 База данных")
    print("├── qr_codes_final/            # 📱 QR-коды")
    print("└── README.md                  # 📖 Документация")
    
    print(f"\n🚀 Проект очищен! Размер уменьшен на ~{deleted_files + deleted_dirs * 5} файлов")

if __name__ == "__main__":
    # Подтверждение перед удалением
    print("⚠️  ВНИМАНИЕ! Будут удалены следующие файлы:")
    print("   • 17 отчетов и документации")
    print("   • 18 тестовых файлов")
    print("   • 5 дублирующихся скриптов персонала")
    print("   • 7 дублирующихся QR генераторов")
    print("   • 8 файлов инициализации БД")
    print("   • 6 папок с дублирующимися QR-кодами")
    print("   • Кэш Python")
    print(f"\n📊 ИТОГО: ~57 файлов и папок")
    
    confirm = input("\n❓ Продолжить очистку? (да/нет): ").strip().lower()
    if confirm in ['да', 'yes', 'y', 'д']:
        cleanup_project()
    else:
        print("❌ Очистка отменена.")
