#!/usr/bin/env python3
# test_reports_new.py - Тест новой системы отчетов

import sys
import datetime
import pytz
sys.path.append('.')

import database
from handlers.admin_panel import generate_daily_report_text

def test_current_shift_report():
    """Тестируем отчет по текущей смене."""
    print("🔥 Тестируем отчет по ТЕКУЩЕЙ смене...")
    
    tz_moscow = pytz.timezone('Europe/Moscow')
    current_time = datetime.datetime.now(tz_moscow)
    
    # Определяем начало ТЕКУЩЕЙ смены
    if current_time.hour >= 12:
        # Текущая смена началась сегодня в 12:00
        start_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        end_time = current_time  # До сейчас
        print(f"Смена идет: с {start_time} до {end_time}")
    else:
        # Текущая смена началась вчера в 12:00
        start_time = (current_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        end_time = current_time  # До сейчас
        print(f"Утренняя смена: с {start_time} до {end_time}")
    
    # Получаем данные
    general_stats = database.get_report_data_for_period(start_time, end_time)
    staff_stats = database.get_staff_performance_for_period(start_time, end_time)
    iiko_count = database.get_iiko_nastoika_count_for_date(end_time.date())
    
    print(f"Данные: выдано={general_stats[0]}, погашено={general_stats[1]}")
    
    if general_stats[0] > 0:
        report_text = generate_daily_report_text(start_time, end_time, general_stats, staff_stats, iiko_count, is_current_shift=True)
        print("\n" + "="*50)
        print(report_text)
        print("="*50)
    else:
        print("❌ Нет данных за этот период")

def test_completed_shift_report():
    """Тестируем отчет по завершенной смене."""
    print("\n📊 Тестируем отчет по ЗАВЕРШЕННОЙ смене...")
    
    tz_moscow = pytz.timezone('Europe/Moscow')
    current_time = datetime.datetime.now(tz_moscow)
    
    # Всегда берем завершенную смену (вчерашнюю)
    if current_time.hour >= 12:
        # Сейчас дневное время - берем смену: вчера 12:00 - сегодня 06:00
        end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (current_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        print(f"Завершенная смена: с {start_time} до {end_time}")
    else:
        # Сейчас утро - берем смену: позавчера 12:00 - вчера 06:00
        end_time = (current_time - datetime.timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (current_time - datetime.timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)
        print(f"Завершенная смена (утром): с {start_time} до {end_time}")
    
    # Получаем данные
    general_stats = database.get_report_data_for_period(start_time, end_time)
    staff_stats = database.get_staff_performance_for_period(start_time, end_time)
    iiko_count = database.get_iiko_nastoika_count_for_date(end_time.date())
    
    print(f"Данные: выдано={general_stats[0]}, погашено={general_stats[1]}")
    
    if general_stats[0] > 0:
        report_text = generate_daily_report_text(start_time, end_time, general_stats, staff_stats, iiko_count, is_current_shift=False)
        print("\n" + "="*50)
        print(report_text)
        print("="*50)
    else:
        print("❌ Нет данных за этот период")

def check_database_data():
    """Проверяем что есть в базе данных."""
    print("📊 Проверяем данные в базе...")
    
    # Проверяем за последние 3 дня
    tz_moscow = pytz.timezone('Europe/Moscow')
    end_time = datetime.datetime.now(tz_moscow)
    start_time = end_time - datetime.timedelta(days=3)
    
    general_stats = database.get_report_data_for_period(start_time, end_time)
    print(f"За последние 3 дня: выдано={general_stats[0]}, погашено={general_stats[1]}")
    
    # Проверяем за вчера
    yesterday = end_time - datetime.timedelta(days=1)
    start_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    general_stats_yesterday = database.get_report_data_for_period(start_yesterday, end_yesterday)
    print(f"За вчера (весь день): выдано={general_stats_yesterday[0]}, погашено={general_stats_yesterday[1]}")

if __name__ == "__main__":
    print("🧪 Тестирование новой системы отчетов")
    print("="*50)
    
    check_database_data()
    test_current_shift_report()
    test_completed_shift_report()
