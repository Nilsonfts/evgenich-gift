#!/usr/bin/env python3
"""
Тестирование системы сбора профилей пользователей
"""

import sqlite3
import database
import texts

def test_database_functions():
    """Тестирует функции базы данных для работы с профилями"""
    print("🔍 Тестирование функций базы данных...")
    
    # Инициализируем БД
    database.init_database()
    
    test_user_id = 999999999  # Тестовый ID
    test_phone = "+79991234567"
    test_name = "Иван Тестович"
    test_birth_date = "15.03.1990"
    
    try:
        # Тестируем добавление пользователя
        if database.add_user(test_user_id, "TestUser", "test_user"):
            print("✅ Пользователь добавлен")
        
        # Тестируем обновление контакта
        if database.update_user_contact(test_user_id, test_phone):
            print("✅ Контакт обновлен")
        
        # Тестируем обновление имени
        if database.update_user_name(test_user_id, test_name):
            print("✅ Имя обновлено")
        
        # Тестируем обновление даты рождения
        if database.update_user_birth_date(test_user_id, test_birth_date):
            print("✅ Дата рождения обновлена и профиль завершен")
        
        # Проверяем данные пользователя
        user_data = database.find_user_by_id(test_user_id)
        if user_data:
            print("📊 Данные пользователя:")
            print(f"   📱 Телефон: {user_data['phone_number']}")
            print(f"   👤 Имя: {user_data['real_name']}")
            print(f"   🎂 Дата рождения: {user_data['birth_date']}")
            print(f"   ✅ Профиль завершен: {'Да' if user_data['profile_completed'] else 'Нет'}")
        
        # Очищаем тестовые данные
        conn = sqlite3.connect(database.DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = ?", (test_user_id,))
        conn.commit()
        conn.close()
        print("🗑️ Тестовые данные удалены")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

def test_texts():
    """Проверяет наличие всех необходимых текстов"""
    print("\n📝 Проверка текстов...")
    
    required_texts = [
        'NAME_REQUEST_TEXT',
        'NAME_RECEIVED_TEXT', 
        'BIRTH_DATE_REQUEST_TEXT',
        'BIRTH_DATE_ERROR_TEXT',
        'PROFILE_COMPLETED_TEXT'
    ]
    
    for text_name in required_texts:
        if hasattr(texts, text_name):
            text_value = getattr(texts, text_name)
            print(f"✅ {text_name}: {text_value[:50]}...")
        else:
            print(f"❌ {text_name}: НЕ НАЙДЕН")

def test_date_validation():
    """Тестирует валидацию дат"""
    print("\n📅 Тестирование валидации дат...")
    
    import re
    import datetime
    
    test_dates = [
        ("15.03.1990", True),
        ("29.02.2020", True),  # Високосный год
        ("29.02.2021", False), # Не високосный год
        ("32.01.2000", False), # Неверный день
        ("15.13.2000", False), # Неверный месяц
        ("15/03/1990", False), # Неверный формат
        ("15.3.1990", False),  # Неверный формат
    ]
    
    for date_str, should_be_valid in test_dates:
        try:
            # Проверяем формат
            if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
                is_valid = False
            else:
                # Проверяем валидность даты
                day, month, year = map(int, date_str.split('.'))
                birth_date = datetime.date(year, month, day)
                
                # Проверяем, что дата не в будущем
                today = datetime.date.today()
                is_valid = birth_date <= today
            
            result = "✅" if is_valid == should_be_valid else "❌"
            print(f"{result} {date_str}: {'валидная' if is_valid else 'невалидная'}")
            
        except (ValueError, TypeError):
            is_valid = False
            result = "✅" if is_valid == should_be_valid else "❌"
            print(f"{result} {date_str}: невалидная (исключение)")

if __name__ == "__main__":
    print("🚀 Запуск тестов системы сбора профилей\n")
    
    test_database_functions()
    test_texts()
    test_date_validation()
    
    print("\n🎉 Тестирование завершено!")
