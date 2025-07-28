#!/usr/bin/env python3
# test_date_parsing.py
from datetime import datetime, timedelta
import re

def parse_booking_date(date_text: str) -> str:
    """
    Преобразует текст даты в формат DD.MM.YYYY.
    Обрабатывает: завтра, послезавтра, дни недели, конкретные даты.
    """
    today = datetime.now()
    date_text = date_text.lower().strip()
    
    # Дни недели (с предлогами и без) и их склонения
    weekdays = {
        'понедельник': 0, 'понедельник': 0,
        'вторник': 1, 'вторник': 1,
        'среда': 2, 'среду': 2,
        'четверг': 3, 'четверг': 3,
        'пятница': 4, 'пятницу': 4,
        'суббота': 5, 'субботу': 5,
        'воскресенье': 6, 'воскресенье': 6,
        'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5, 'вс': 6
    }
    
    # Сегодня
    if 'сегодня' in date_text:
        return today.strftime('%d.%m.%Y')
    
    # Завтра
    if 'завтра' in date_text and 'послезавтра' not in date_text:
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime('%d.%m.%Y')
    
    # Послезавтра
    if 'послезавтра' in date_text:
        day_after_tomorrow = today + timedelta(days=2)
        return day_after_tomorrow.strftime('%d.%m.%Y')
    
    # Дни недели (учитываем предлоги)
    for day_name, day_num in weekdays.items():
        # Проверяем разные варианты написания
        patterns = [day_name, f"в {day_name}", f"во {day_name}"]
        for pattern in patterns:
            if pattern in date_text:
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # Если день уже прошел на этой неделе, берем следующую неделю
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%d.%m.%Y')
    
    # Попытка распарсить числовую дату
    # Форматы: 15.08, 15.08.2025, 15/08, 15/08/2025, 15 августа и т.д.
    
    # DD.MM или DD/MM
    date_pattern = r'(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?'
    match = re.search(date_pattern, date_text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:  # Если год двузначный
            year += 2000
        
        try:
            target_date = datetime(year, month, day)
            return target_date.strftime('%d.%m.%Y')
        except ValueError:
            pass
    
    # Если ничего не распознали, просто возвращаем исходный текст
    return date_text

def test_date_parsing():
    """Тестовая функция для проверки парсинга дат."""
    test_dates = [
        "завтра", "послезавтра", "в субботу", "в понедельник", 
        "15.08", "15.08.2025", "15/08", "15 августа", "сегодня",
        "в пятницу", "во вторник", "29.07", "30/07/2025"
    ]
    
    print(f"Сегодня: {datetime.now().strftime('%d.%m.%Y (%A)')}")
    print("=" * 50)
    print("Тестирование парсинга дат:")
    for date_str in test_dates:
        parsed = parse_booking_date(date_str)
        print(f"'{date_str}' -> '{parsed}'")

if __name__ == "__main__":
    test_date_parsing()
