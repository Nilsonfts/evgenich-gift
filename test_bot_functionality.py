#!/usr/bin/env python3
"""
Тестовый скрипт для проверки основных функций бота.
"""

import sys
import os
import logging

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тестируем импорты всех модулей."""
    print("🔍 Тестирование импортов...")
    
    try:
        import config
        print("✅ config.py - OK")
    except Exception as e:
        print(f"❌ config.py - ОШИБКА: {e}")
        
    try:
        import database
        print("✅ database.py - OK")
    except Exception as e:
        print(f"❌ database.py - ОШИБКА: {e}")
        
    try:
        import keyboards
        print("✅ keyboards.py - OK")
    except Exception as e:
        print(f"❌ keyboards.py - ОШИБКА: {e}")
        
    try:
        import texts
        print("✅ texts.py - OK")
    except Exception as e:
        print(f"❌ texts.py - ОШИБКА: {e}")
        
    try:
        from handlers import callback_query
        print("✅ handlers/callback_query.py - OK")
    except Exception as e:
        print(f"❌ handlers/callback_query.py - ОШИБКА: {e}")
        
    try:
        from handlers import user_commands
        print("✅ handlers/user_commands.py - OK")
    except Exception as e:
        print(f"❌ handlers/user_commands.py - ОШИБКА: {e}")
        
    try:
        from handlers import admin_panel
        print("✅ handlers/admin_panel.py - OK")
    except Exception as e:
        print(f"❌ handlers/admin_panel.py - ОШИБКА: {e}")
        
    try:
        from handlers import ai_logic
        print("✅ handlers/ai_logic.py - OK")
    except Exception as e:
        print(f"❌ handlers/ai_logic.py - ОШИБКА: {e}")
        
    try:
        from ai import assistant
        print("✅ ai/assistant.py - OK")
    except Exception as e:
        print(f"❌ ai/assistant.py - ОШИБКА: {e}")

def test_database_functions():
    """Тестируем функции базы данных."""
    print("\n🗄️ Тестирование функций базы данных...")
    
    try:
        import database
        
        # Инициализируем базу данных
        database.init_db()
        print("✅ Инициализация базы данных - OK")
        
        # Тестируем функции концепций
        test_user_id = 12345
        database.update_user_concept(test_user_id, "rvv")
        concept = database.get_user_concept(test_user_id)
        if concept == "rvv":
            print("✅ Функции концепций работают - OK")
        else:
            print(f"❌ Функции концепций - ОШИБКА: ожидалось 'rvv', получено '{concept}'")
            
    except Exception as e:
        print(f"❌ Тестирование базы данных - ОШИБКА: {e}")

def test_keyboards():
    """Тестируем создание клавиатур."""
    print("\n⌨️ Тестирование клавиатур...")
    
    try:
        import keyboards
        
        # Тестируем клавиатуру концепций
        concept_keyboard = keyboards.get_concept_choice_keyboard()
        if concept_keyboard.keyboard:
            print("✅ Клавиатура концепций создается - OK")
        else:
            print("❌ Клавиатура концепций - ОШИБКА: пустая клавиатура")
            
        # Тестируем основные клавиатуры
        main_keyboard = keyboards.get_main_menu_keyboard(12345)
        if main_keyboard.keyboard:
            print("✅ Главная клавиатура создается - OK")
        else:
            print("❌ Главная клавиатура - ОШИБКА: пустая клавиатура")
            
    except Exception as e:
        print(f"❌ Тестирование клавиатур - ОШИБКА: {e}")

def test_ai_concepts():
    """Тестируем AI концепции."""
    print("\n🤖 Тестирование AI концепций...")
    
    try:
        from ai.assistant import create_system_prompt
        
        # Тестируем разные концепции
        concepts = ["evgenich", "rvv", "nebar", "spletni", "orbita"]
        
        for concept in concepts:
            prompt = create_system_prompt("тестовые данные", concept)
            if concept.upper() in prompt or concept in prompt:
                print(f"✅ Концепция '{concept}' - OK")
            else:
                print(f"❌ Концепция '{concept}' - ОШИБКА: концепция не найдена в промпте")
                
    except Exception as e:
        print(f"❌ Тестирование AI концепций - ОШИБКА: {e}")

def test_environment_variables():
    """Проверяем переменные окружения."""
    print("\n🌍 Проверка переменных окружения...")
    
    try:
        import config
        
        # Критически важные переменные
        critical_vars = [
            ("BOT_TOKEN", config.BOT_TOKEN),
            ("CHANNEL_ID", config.CHANNEL_ID),
            ("ADMIN_IDS", config.ADMIN_IDS)
        ]
        
        for var_name, var_value in critical_vars:
            if var_value:
                print(f"✅ {var_name} - установлена")
            else:
                print(f"❌ {var_name} - НЕ УСТАНОВЛЕНА (критично!)")
        
        # Опциональные переменные
        optional_vars = [
            ("OPENAI_API_KEY", config.OPENAI_API_KEY),
            ("GOOGLE_SHEET_KEY", config.GOOGLE_SHEET_KEY),
            ("REPORT_CHAT_ID", config.REPORT_CHAT_ID)
        ]
        
        for var_name, var_value in optional_vars:
            if var_value:
                print(f"✅ {var_name} - установлена")
            else:
                print(f"⚠️ {var_name} - не установлена (опционально)")
                
    except Exception as e:
        print(f"❌ Проверка переменных окружения - ОШИБКА: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования бота 'Евгенич'...\n")
    
    # Настраиваем логирование для тестов
    logging.basicConfig(level=logging.WARNING)
    
    # Запускаем все тесты
    test_imports()
    test_environment_variables()
    test_database_functions()
    test_keyboards()
    test_ai_concepts()
    
    print("\n✅ Тестирование завершено!")
    print("\n📋 Рекомендации:")
    print("1. Убедитесь, что все критичные переменные окружения установлены")
    print("2. Проверьте логи на наличие ошибок")
    print("3. Протестируйте бота в Telegram с командой /concept")
    print("4. Если кнопки не работают, проверьте логи callback'ов")
