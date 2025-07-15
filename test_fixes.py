#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования исправлений:
1. Правильное формирование периода отчета (12:00-06:00)
2. Корректная работа системы QR-кодов сотрудников
"""

import datetime
import pytz
import database

def test_report_period():
    """Тестирует логику формирования периода отчета"""
    print("=== ТЕСТ ПЕРИОДА ОТЧЕТА ===")
    
    tz_moscow = pytz.timezone('Europe/Moscow')
    test_times = [
        datetime.datetime(2025, 7, 16, 5, 30),   # 05:30 - до 06:00
        datetime.datetime(2025, 7, 16, 8, 0),    # 08:00 - после 06:00, до 12:00  
        datetime.datetime(2025, 7, 16, 14, 0),   # 14:00 - после 12:00
        datetime.datetime(2025, 7, 16, 23, 0),   # 23:00 - поздний вечер
    ]
    
    for current_time in test_times:
        current_time = tz_moscow.localize(current_time)
        print(f"\nТекущее время: {current_time.strftime('%d.%m.%Y %H:%M')}")
        
        # Применяем ту же логику, что в исправленном коде
        if current_time.hour < 12:
            end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            if current_time.hour >= 6:
                pass
            else:
                end_time = end_time - datetime.timedelta(days=1)
            start_time = (end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        
        print(f"Период отчета: {start_time.strftime('%d.%m.%Y %H:%M')} - {end_time.strftime('%d.%m.%Y %H:%M')}")
        hours_diff = (end_time - start_time).total_seconds() / 3600
        print(f"Продолжительность: {hours_diff} часов")

def test_staff_system():
    """Тестирует систему сотрудников"""
    print("\n=== ТЕСТ СИСТЕМЫ СОТРУДНИКОВ ===")
    
    # Инициализируем базу данных
    database.init_db()
    
    # Получаем список всех сотрудников
    all_staff = database.get_all_staff()
    print(f"Всего сотрудников в базе: {len(all_staff)}")
    
    for staff in all_staff:
        print(f"- {staff['full_name']} ({staff['position']}) - код: {staff['unique_code']} - статус: {staff['status']}")
    
    # Тестируем поиск по коду
    if all_staff:
        test_code = all_staff[0]['unique_code']
        found_staff = database.find_staff_by_code(test_code)
        if found_staff:
            print(f"\n✅ Поиск по коду '{test_code}' успешен: {found_staff['full_name']}")
        else:
            print(f"\n❌ Поиск по коду '{test_code}' неудачен")

def test_staff_performance():
    """Тестирует получение статистики сотрудников"""
    print("\n=== ТЕСТ СТАТИСТИКИ СОТРУДНИКОВ ===")
    
    tz_moscow = pytz.timezone('Europe/Moscow')
    current_time = datetime.datetime.now(tz_moscow)
    
    # За последние 24 часа
    start_time = current_time - datetime.timedelta(days=1)
    
    staff_stats = database.get_staff_performance_for_period(start_time, current_time)
    
    if not staff_stats:
        print("За последние 24 часа статистики по сотрудникам нет")
    else:
        print("Статистика сотрудников за последние 24 часа:")
        for position, staff_list in staff_stats.items():
            print(f"\n{position}:")
            for staff_member in staff_list:
                print(f"  - {staff_member['name']}: {staff_member['brought']} приведено, {staff_member['churn']} отток")

if __name__ == "__main__":
    test_report_period()
    test_staff_system()
    test_staff_performance()
    print("\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
