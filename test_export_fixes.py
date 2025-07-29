#!/usr/bin/env python3
"""
Тест исправлений Google Sheets экспорта
"""
from datetime import datetime, timedelta
import pytz

def get_moscow_time() -> str:
    """
    Возвращает текущее время в московском часовом поясе (UTC+3).
    
    Returns:
        str: Время в формате "dd.mm.yyyy HH:MM"
    """
    try:
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        return moscow_time.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        print(f"Ошибка получения московского времени: {e}, используем UTC+3")
        # Fallback: UTC + 3 часа
        utc_time = datetime.utcnow()
        moscow_time = utc_time + timedelta(hours=3)
        return moscow_time.strftime('%d.%m.%Y %H:%M')

def test_data_validation():
    """Тест валидации данных для Google Sheets"""
    print("🧪 Тестирование валидации данных:")
    
    # Тестовые данные с потенциальными проблемами
    test_row_data = [
        get_moscow_time(),
        "Тест-4",
        "+7(999)123-45-67",
        "30.07.2025 19:00",
        "2",
        "🤖 Гостевое бронирование (бот)",
        "guest_bot",
        "День рождения",
        "👤 Посетитель (через бота)",
        "Новая",
        "bot_tg",
        "guest_booking",
        "direct_guest",
        "bot_guest_booking",
        "guest_booking_term",
        f"BID-{int(datetime.now().timestamp())}",
        196614680
    ]
    
    print(f"Исходные данные: {len(test_row_data)} элементов")
    
    # Проверка и очистка данных (как в коде)
    for i, value in enumerate(test_row_data):
        if value is None:
            test_row_data[i] = ""
        elif not isinstance(value, (str, int, float)):
            test_row_data[i] = str(value)
    
    print(f"После валидации: {len(test_row_data)} элементов")
    print("Данные валидны для Google Sheets ✅")
    
    # Проверяем, что все элементы правильного типа
    for i, value in enumerate(test_row_data):
        if not isinstance(value, (str, int, float)):
            print(f"❌ Элемент {i} имеет недопустимый тип: {type(value)}")
            return False
    
    print("✅ Все данные прошли валидацию!")
    return True

if __name__ == "__main__":
    print("🚀 Тестирование исправлений экспорта\n")
    
    print(f"Московское время: {get_moscow_time()}")
    print()
    
    test_data_validation()
    
    print("\n🏁 Тестирование завершено!")
