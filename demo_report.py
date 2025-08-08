#!/usr/bin/env python3
"""
Демонстрирует работу исправленной системы отчетов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Устанавливаем минимальные переменные окружения для тестирования
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['CHANNEL_ID'] = '123'
os.environ['ADMIN_IDS'] = '123'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'

from datetime import datetime
from handlers.admin_panel import generate_daily_report_text, send_report
import database

def demo_report():
    """Демонстрирует работу отчета с реальными данными"""
    print("🎯 ДЕМОНСТРАЦИЯ ИСПРАВЛЕННОЙ СИСТЕМЫ ОТЧЕТОВ")
    print("=" * 50)
    
    # Период из сообщения пользователя
    start_time = datetime(2025, 8, 8, 12, 0)
    end_time = datetime(2025, 8, 8, 16, 44)
    
    print(f"📅 Период: {start_time.strftime('%d.%m %H:%M')} - {end_time.strftime('%d.%m %H:%M')}")
    print()
    
    try:
        # Получаем данные через исправленные функции
        general_stats = database.get_report_data_for_period(start_time, end_time)
        staff_stats = database.get_staff_performance_for_period(start_time, end_time)
        
        # Проверяем, есть ли данные
        if general_stats[0] == 0:
            print("❌ ОШИБКА: Все еще нет данных!")
            print("За период с 08.08 12:00 по 08.08 16:44 нет данных для отчета по текущей смены.")
            return
        
        print("✅ УСПЕХ: Данные найдены!")
        print(f"Найдено {general_stats[0]} выданных подарков")
        print()
        
        # Генерируем текст отчета
        report_text = generate_daily_report_text(
            start_time, end_time, general_stats, staff_stats, 
            iiko_count=85, is_current_shift=True
        )
        
        print("📋 СГЕНЕРИРОВАННЫЙ ОТЧЕТ:")
        print("-" * 40)
        print(report_text)
        print("-" * 40)
        
        print()
        print("🎉 СИСТЕМА ОТЧЕТОВ РАБОТАЕТ КОРРЕКТНО!")
        print("✅ Проблема с 'нет данных для отчета' РЕШЕНА")
        
    except Exception as e:
        print(f"❌ Ошибка при генерации отчета: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_report()
