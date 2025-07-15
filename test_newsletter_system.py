#!/usr/bin/env python3
# test_newsletter_system.py

import sys
import os
sys.path.append('/workspaces/evgenich-gift')

def test_newsletter_system():
    """Тестирует компоненты системы рассылок."""
    try:
        print("🔍 Тестирование системы рассылок...")
        
        # Тестируем импорт модулей
        import database
        print("✓ Database импортирован")
        
        import keyboards  
        print("✓ Keyboards импортирован")
        
        import texts
        print("✓ Texts импортирован")
        
        # Тестируем функции клавиатур рассылок
        content_menu = keyboards.get_content_management_menu()
        print("✓ Клавиатура управления контентом создана")
        
        newsletter_menu = keyboards.get_newsletter_creation_menu()
        print("✓ Клавиатура создания рассылки создана")
        
        sending_menu = keyboards.get_newsletter_sending_menu(1)
        print("✓ Клавиатура отправки рассылки создана")
        
        # Тестируем тексты рассылок
        newsletter_attrs = [attr for attr in dir(texts) if 'NEWSLETTER' in attr]
        print(f"✓ Найдено {len(newsletter_attrs)} текстов для рассылок")
        
        # Проверяем ключевые тексты
        key_texts = [
            'NEWSLETTER_CREATION_START',
            'NEWSLETTER_READY_TEXT', 
            'NEWSLETTER_TITLE_REQUEST',
            'NEWSLETTER_CONTENT_REQUEST'
        ]
        
        for text_name in key_texts:
            if hasattr(texts, text_name):
                print(f"✓ {text_name} найден")
            else:
                print(f"❌ {text_name} НЕ найден")
        
        # Тестируем функции БД (без подключения к реальной БД)
        db_functions = [
            'create_newsletter',
            'get_newsletter_by_id', 
            'add_newsletter_button',
            'get_newsletter_audience_count'
        ]
        
        for func_name in db_functions:
            if hasattr(database, func_name):
                print(f"✓ Функция БД {func_name} найдена")
            else:
                print(f"❌ Функция БД {func_name} НЕ найдена")
        
        print("\n✅ Тестирование завершено успешно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_newsletter_system()
