#!/usr/bin/env python3
"""
Тестирование исправлений: формат даты DD.MM.YYYY и имя админа
"""

from social_bookings_export import parse_booking_date, get_admin_name_by_id

def test_date_format():
    """Тестируем формат даты DD.MM.YYYY"""
    print("🗓️ ТЕСТИРОВАНИЕ ФОРМАТА ДАТЫ\n")
    
    test_dates = [
        "завтра",
        "послезавтра", 
        "в субботу",
        "в понедельник",
        "15.08",
        "15.08.2025",
        "30 июля",
        "01.08",
        "сегодня"
    ]
    
    print("Проверяем что все даты возвращаются в формате DD.MM.YYYY:")
    print("=" * 50)
    
    for date_str in test_dates:
        parsed = parse_booking_date(date_str)
        print(f"'{date_str}' → '{parsed}'")
        
        # Проверяем формат DD.MM.YYYY
        if len(parsed.split('.')) == 3:
            day, month, year = parsed.split('.')
            if len(day) == 2 and len(month) == 2 and len(year) == 4:
                print(f"   ✅ Формат DD.MM.YYYY корректный")
            else:
                print(f"   ❌ Неправильный формат: {parsed}")
        else:
            print(f"   ⚠️  Не числовая дата: {parsed}")
        print()

def test_admin_name():
    """Тестируем исправленное имя админа"""
    print("\n👤 ТЕСТИРОВАНИЕ ИМЕНИ АДМИНА\n")
    
    admin_id = 196614680
    admin_name = get_admin_name_by_id(admin_id)
    
    print(f"ID админа: {admin_id}")
    print(f"Имя админа: {admin_name}")
    
    if admin_name == "Нил Витальевич":
        print("✅ Имя админа исправлено корректно!")
    else:
        print(f"❌ Ожидалось 'Нил Витальевич', получено '{admin_name}'")

def test_google_sheets_row():
    """Тестируем данные для Google Sheets"""
    print("\n📊 ТЕСТИРОВАНИЕ ДАННЫХ ДЛЯ GOOGLE SHEETS\n")
    
    # Тестовые данные брони
    booking_data = {
        'name': 'Нил Тест',
        'phone': '89996106215', 
        'date': 'завтра',
        'time': '19:30',
        'guests': '5',
        'source': 'source_vk',
        'reason': 'тест системы'
    }
    
    admin_id = 196614680
    
    # Парсим дату
    booking_date = parse_booking_date(booking_data.get('date', ''))
    admin_name = get_admin_name_by_id(admin_id)
    
    print("Данные которые попадут в Google Sheets:")
    print(f"A (Дата Заявки): {booking_date}")  # Будет текущая дата
    print(f"B (Имя Гостя): {booking_data.get('name', '')}")
    print(f"C (Телефон): {booking_data.get('phone', '')}")
    print(f"D (Дата посещения): {booking_date}")  # Формат DD.MM.YYYY
    print(f"E (Время): {booking_data.get('time', '')}")
    print(f"F (Кол-во гостей): {booking_data.get('guests', '')}")
    print(f"G (Источник): ВКонтакте")
    print(f"H (ТЕГ для АМО): vk")
    print(f"I (Повод Визита): {booking_data.get('reason', '')}")
    print(f"J (Кто создал заявку): {admin_name}")  # Должно быть "Нил Витальевич"
    print(f"K (Статус): Новая")

if __name__ == "__main__":
    test_date_format()
    test_admin_name()
    test_google_sheets_row()
