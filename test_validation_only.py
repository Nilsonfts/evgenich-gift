#!/usr/bin/env python3
"""
Тестирование логики валидации дат без зависимостей
"""

import re
import datetime

def test_date_validation():
    """Тестирует валидацию дат рождения"""
    print("📅 Тестирование валидации дат рождения...")
    
    test_cases = [
        ("15.03.1990", True, "Обычная дата"),
        ("29.02.2020", True, "Високосный год"),
        ("29.02.2021", False, "Не високосный год"),
        ("32.01.2000", False, "Неверный день"),
        ("15.13.2000", False, "Неверный месяц"),
        ("15/03/1990", False, "Неверный формат"),
        ("15.3.1990", False, "Неверный формат"),
        ("1.01.2000", False, "Однозначный день"),
        ("01.1.2000", False, "Однозначный месяц"),
        ("01.01.2030", False, "Дата в будущем"),
        ("01.01.1920", False, "Слишком старая дата"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for date_str, expected, description in test_cases:
        try:
            # Проверяем формат DD.MM.YYYY
            if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
                is_valid = False
                error_reason = "неверный формат"
            else:
                # Проверяем валидность даты
                day, month, year = map(int, date_str.split('.'))
                birth_date = datetime.date(year, month, day)
                
                # Проверяем, что дата не в будущем и не слишком старая
                today = datetime.date.today()
                if birth_date > today:
                    is_valid = False
                    error_reason = "дата в будущем"
                else:
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    if age > 100:
                        is_valid = False
                        error_reason = "слишком старая дата"
                    else:
                        is_valid = True
                        error_reason = "валидная"
            
        except (ValueError, TypeError) as e:
            is_valid = False
            error_reason = f"исключение: {str(e)}"
        
        # Проверяем результат
        result_correct = is_valid == expected
        if result_correct:
            passed += 1
            
        status = "✅ PASS" if result_correct else "❌ FAIL"
        print(f"{status} {date_str:12} | {description:20} | {error_reason}")
    
    print(f"\n📊 Результат: {passed}/{total} тестов пройдено")
    return passed == total

def test_name_validation():
    """Тестирует валидацию имен"""
    print("\n👤 Тестирование валидации имен...")
    
    test_cases = [
        ("Иван", True, "Обычное имя"),
        ("Анна-Мария", True, "Имя с дефисом"),
        ("Екатерина Александровна", True, "Имя с отчеством"),
        ("А", False, "Слишком короткое"),
        ("", False, "Пустое"),
        ("А" * 51, False, "Слишком длинное"),
        ("Иван123", True, "С цифрами (допустимо)"),
        ("   Иван   ", True, "С пробелами (обрезается)"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for name, expected, description in test_cases:
        # Логика валидации имени
        clean_name = name.strip()
        is_valid = 2 <= len(clean_name) <= 50
        
        result_correct = is_valid == expected
        if result_correct:
            passed += 1
            
        status = "✅ PASS" if result_correct else "❌ FAIL"
        print(f"{status} '{name}' ({len(clean_name)} символов) | {description}")
    
    print(f"\n📊 Результат: {passed}/{total} тестов пройдено")
    return passed == total

def main():
    print("🚀 Тестирование валидации данных профиля\n")
    
    dates_ok = test_date_validation()
    names_ok = test_name_validation()
    
    if dates_ok and names_ok:
        print("\n🎉 Все тесты валидации пройдены успешно!")
    else:
        print("\n⚠️ Некоторые тесты не прошли проверку")

if __name__ == "__main__":
    main()
