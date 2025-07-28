#!/usr/bin/env python3
"""
Тестирование улучшенного парсинга даты и времени
"""

from social_bookings_export import parse_booking_date, parse_booking_time

def test_date_parsing():
    """Тестируем парсинг дат в разных форматах"""
    print("🗓️ ТЕСТИРОВАНИЕ ПАРСИНГА ДАТ\n")
    
    test_dates = [
        "завтра",
        "послезавтра", 
        "в субботу",
        "в понедельник",
        "11 августа",
        "15 июля",
        "30 мая",
        "11.08",
        "15.07",
        "30.12",
        "11 08",
        "15 07", 
        "30 12",
        "сегодня"
    ]
    
    print("Тестируем различные форматы дат:")
    print("=" * 50)
    
    for date_str in test_dates:
        parsed = parse_booking_date(date_str)
        print(f"'{date_str}' → '{parsed}'")
        
def test_time_parsing():
    """Тестируем парсинг времени в разных форматах"""
    print("\n🕒 ТЕСТИРОВАНИЕ ПАРСИНГА ВРЕМЕНИ\n")
    
    test_times = [
        "19:30",
        "19.30", 
        "19 30",
        "1930",
        "7:30",
        "07:30",
        "7.30",
        "730",
        "23:59",
        "00:00",
        "12:15",
        "1215"
    ]
    
    print("Тестируем различные форматы времени:")
    print("=" * 50)
    
    for time_str in test_times:
        parsed = parse_booking_time(time_str)
        print(f"'{time_str}' → '{parsed}'")

def test_complete_booking_flow():
    """Тестируем полный поток данных бронирования"""
    print("\n📋 ТЕСТИРОВАНИЕ ПОЛНОГО ПОТОКА БРОНИРОВАНИЯ\n")
    
    test_booking = {
        'name': 'Нил Тест',
        'phone': '89996106215',
        'date': '11 августа',
        'time': '19:30',
        'guests': '5',
        'source': 'source_vk',
        'reason': 'день рождения'
    }
    
    print("Исходные данные:")
    for key, value in test_booking.items():
        print(f"  {key}: {value}")
    
    print("\nОбработанные данные:")
    processed_date = parse_booking_date(test_booking['date'])
    processed_time = parse_booking_time(test_booking['time'])
    
    print(f"  date: {test_booking['date']} → {processed_date}")
    print(f"  time: {test_booking['time']} → {processed_time}")
    
    print(f"\nИтоговые данные для Google Sheets:")
    print(f"  D (Дата посещения): {processed_date}")
    print(f"  E (Время): {processed_time}")

if __name__ == "__main__":
    test_date_parsing()
    test_time_parsing()
    test_complete_booking_flow()
