#!/usr/bin/env python3
"""
Тест PostgreSQL функций отчетов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Устанавливаем переменные окружения для тестирования
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['CHANNEL_ID'] = '123'
os.environ['ADMIN_IDS'] = '123'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'
os.environ['USE_POSTGRES'] = 'true'  # Включаем PostgreSQL

from datetime import datetime
from config import USE_POSTGRES
import database

def test_postgres_reports():
    """Тестирует PostgreSQL функции отчетов"""
    print("🔍 ТЕСТИРОВАНИЕ POSTGRESQL ОТЧЕТОВ")
    print("=" * 50)
    
    print(f"USE_POSTGRES: {USE_POSTGRES}")
    print(f"pg_client доступен: {database.pg_client is not None}")
    
    # Период из сообщения пользователя
    start_time = datetime(2025, 8, 8, 12, 0)
    end_time = datetime(2025, 8, 8, 17, 1)  # Обновленный период из скриншота
    
    print(f"📅 Тестовый период: {start_time.strftime('%d.%m %H:%M')} - {end_time.strftime('%d.%m %H:%M')}")
    print()
    
    try:
        # Тестируем PostgreSQL функции напрямую
        if database.pg_client:
            print("🔗 Тестируем прямые вызовы к PostgreSQL...")
            
            # Прямой вызов к pg_client
            pg_result = database.pg_client.get_report_data_for_period(start_time, end_time)
            print(f"📊 PostgreSQL результат: {pg_result}")
            
            pg_churn = database.pg_client.get_daily_churn_data(start_time, end_time)
            print(f"📉 PostgreSQL отток: {pg_churn}")
        
        print()
        print("🔗 Тестируем основные функции database.py...")
        
        # Тестируем основные функции
        general_stats = database.get_report_data_for_period(start_time, end_time)
        issued, redeemed, _, sources, total_time = general_stats
        
        print(f"✅ Выдано подарков: {issued}")
        print(f"✅ Активировано подарков: {redeemed}")
        print(f"✅ Источники: {sources}")
        print(f"✅ Время активации: {total_time} сек.")
        
        churn_data = database.get_daily_churn_data(start_time, end_time)
        print(f"✅ Отток: активировано {churn_data[0]}, ушло {churn_data[1]}")
        
        print()
        
        # Проверяем результат
        if issued == 0:
            print("❌ ПРОБЛЕМА НЕ РЕШЕНА")
            print("PostgreSQL функции не находят данные или не работают корректно")
        else:
            print("✅ ПРОБЛЕМА РЕШЕНА!")
            print(f"PostgreSQL нашел {issued} выданных подарков за период")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_postgres_reports()
