#!/usr/bin/env python3
"""
Простой тест московского времени без импорта конфига
"""
import pytz
from datetime import datetime

def get_moscow_time() -> str:
    """
    Возвращает текущее время в московском часовом поясе (UTC+3).
    
    Returns:
        str: Время в формате "dd.mm.yyyy HH:MM"
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(moscow_tz)
    return moscow_time.strftime('%d.%m.%Y %H:%M')

def test_moscow_time():
    """Тестирует функцию московского времени"""
    print("🕐 Тестирование московского времени:")
    
    # Текущее UTC время
    utc_time = datetime.now(pytz.UTC)
    print(f"UTC время: {utc_time.strftime('%d.%m.%Y %H:%M:%S %Z')}")
    
    # Московское время
    moscow_dt = datetime.now(pytz.timezone('Europe/Moscow'))
    moscow_formatted = get_moscow_time()
    print(f"Московское время (объект): {moscow_dt.strftime('%d.%m.%Y %H:%M:%S %Z')}")
    print(f"Московское время (функция): {moscow_formatted}")
    
    # Проверяем разность (должна быть 3 часа)
    diff_hours = (moscow_dt.replace(tzinfo=None) - utc_time.replace(tzinfo=None)).total_seconds() / 3600
    print(f"Разность с UTC: {diff_hours:.1f} часов")
    
    if abs(diff_hours - 3.0) < 0.1:  # Учитываем летнее время
        print("✅ Московское время работает корректно!")
    else:
        print("⚠️  Возможна проблема с часовым поясом")
    
    print()

if __name__ == "__main__":
    print("🚀 Тестирование московского времени\n")
    test_moscow_time()
    print("🏁 Тестирование завершено!")
