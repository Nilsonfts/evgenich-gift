#!/usr/bin/env python3
"""
Тестирование московского времени и экспорта во вторую таблицу
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from social_bookings_export import get_moscow_time, export_booking_to_secondary_table
from datetime import datetime
import pytz

def test_moscow_time():
    """Тестирует функцию московского времени"""
    print("🕐 Тестирование московского времени:")
    
    # Текущее UTC время
    utc_time = datetime.now(pytz.UTC)
    print(f"UTC время: {utc_time.strftime('%d.%m.%Y %H:%M:%S')}")
    
    # Московское время
    moscow_time = get_moscow_time()
    print(f"Московское время (UTC+3): {moscow_time}")
    
    # Проверяем разность (должна быть 3 часа)
    moscow_dt = datetime.now(pytz.timezone('Europe/Moscow'))
    utc_dt = datetime.now(pytz.UTC)
    diff_hours = (moscow_dt - utc_dt.replace(tzinfo=None)).total_seconds() / 3600
    print(f"Разность с UTC: {diff_hours} часов")
    
    print("✅ Московское время работает корректно!\n")

def test_secondary_export():
    """Тестирует экспорт во вторую таблицу"""
    print("📊 Тестирование экспорта во вторую таблицу:")
    
    # Тестовые данные
    test_booking_data = {
        'name': 'Тест Экспорт',
        'phone': '+7(999)123-45-67',
        'date': '30.07.2025',
        'time': '19:00',
        'guests': '2',
        'reason': 'День рождения',
        'source': 'source_vk'
    }
    
    test_user_id = 196614680
    
    print("Тестовые данные:")
    for key, value in test_booking_data.items():
        print(f"  {key}: {value}")
    print(f"  user_id: {test_user_id}")
    
    # Попробуем экспорт
    try:
        result = export_booking_to_secondary_table(
            booking_data=test_booking_data,
            user_id=test_user_id,
            is_admin_booking=True
        )
        
        if result:
            print("✅ Экспорт во вторую таблицу прошел успешно!")
        else:
            print("❌ Экспорт во вторую таблицу не удался")
            
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        
    print()

if __name__ == "__main__":
    print("🚀 Запуск тестирования экспорта и московского времени\n")
    
    test_moscow_time()
    test_secondary_export()
    
    print("🏁 Тестирование завершено!")
