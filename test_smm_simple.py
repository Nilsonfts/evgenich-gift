#!/usr/bin/env python3
"""
Упрощенный тест проверки логики СММщиков
"""

# Имитируем переменные окружения для теста
import os
os.environ['BOT_TOKEN'] = 'test'
os.environ['CHANNEL_ID'] = '123'
os.environ['ADMIN_IDS'] = '123'
os.environ['GOOGLE_SHEET_KEY'] = 'test1,test2'
os.environ['GOOGLE_CREDENTIALS_JSON'] = '{}'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'
# Устанавливаем SMM_IDS для теста
os.environ['SMM_IDS'] = '555666777,888999000'

# Теперь можем импортировать config
from config import SMM_IDS, ALL_BOOKING_STAFF, BOSS_IDS, ADMIN_IDS_LIST

def test_smm_config():
    print("🔍 Проверяем конфигурацию СММщиков:")
    print(f"SMM_IDS: {SMM_IDS}")
    print(f"BOSS_IDS: {BOSS_IDS}")
    print(f"ADMIN_IDS_LIST: {ADMIN_IDS_LIST}")
    print(f"ALL_BOOKING_STAFF: {ALL_BOOKING_STAFF}")
    
    # Проверяем логику
    print(f"\n📝 Анализ логики:")
    print(f"- SMM_IDS пустой: {len(SMM_IDS) == 0}")
    print(f"- ALL_BOOKING_STAFF включает SMM: {set(SMM_IDS).issubset(set(ALL_BOOKING_STAFF))}")
    
    if len(SMM_IDS) == 0:
        print("\n⚠️  ПРОБЛЕМА: SMM_IDS пустой!")
        print("💡 Нужно установить переменную окружения SMM_IDS")
        print("📋 Формат: SMM_IDS='123456789,987654321'")
        return False
    
    return True

def test_booking_flow_logic():
    """Тестируем логику booking_flow"""
    print("\n🔍 Анализ логики booking_flow.py:")
    
    # Имитируем user_id СММщика
    test_smm_id = 555666777  # Пример ID
    
    # Проверяем, попадет ли он в ALL_BOOKING_STAFF
    if test_smm_id in ALL_BOOKING_STAFF:
        print(f"✅ СММщик {test_smm_id} есть в ALL_BOOKING_STAFF")
        
        # Имитируем флаг is_admin_booking
        is_admin_booking = True  # Это устанавливается в handle_admin_booking_entry
        
        print(f"📊 Какую функцию экспорта вызовет:")
        if is_admin_booking:
            print("  → export_social_booking_to_sheets() с admin_id")
            print("  → export_booking_to_secondary_table() с is_admin_booking=True")
        else:
            print("  → export_guest_booking_to_sheets() с user_id")
            print("  → export_booking_to_secondary_table() с is_admin_booking=False")
            
        return True
    else:
        print(f"❌ СММщик {test_smm_id} НЕ в ALL_BOOKING_STAFF")
        return False

if __name__ == "__main__":
    print("🚀 Упрощенный тест логики СММщиков\n")
    
    # Тест 1: конфигурация
    config_ok = test_smm_config()
    
    # Тест 2: логика потока
    flow_ok = test_booking_flow_logic()
    
    print(f"\n📋 РЕЗУЛЬТАТ:")
    print(f"   Конфигурация: {'✅' if config_ok else '❌'}")
    print(f"   Логика потока: {'✅' if flow_ok else '❌'}")
    
    if not config_ok:
        print(f"\n🎯 РЕШЕНИЕ: Установить переменную SMM_IDS в Railway")
