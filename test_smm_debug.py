#!/usr/bin/env python3
"""
Тест для отладки проблемы с СММщиками
"""
import logging
from config import SMM_IDS, ALL_BOOKING_STAFF, BOSS_IDS, ADMIN_IDS_LIST
from social_bookings_export import export_social_booking_to_sheets

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_smm_config():
    print("🔍 Проверяем конфигурацию СММщиков:")
    print(f"SMM_IDS: {SMM_IDS}")
    print(f"BOSS_IDS: {BOSS_IDS}")
    print(f"ADMIN_IDS_LIST: {ADMIN_IDS_LIST}")
    print(f"ALL_BOOKING_STAFF: {ALL_BOOKING_STAFF}")
    
    # Тестовый СММщик ID (замените на реальный ID вашего СММщика)
    test_smm_id = 123456789  # Вставьте сюда ID СММщика
    
    print(f"\n🧪 Тест для ID {test_smm_id}:")
    print(f"В SMM_IDS: {test_smm_id in SMM_IDS}")
    print(f"В ALL_BOOKING_STAFF: {test_smm_id in ALL_BOOKING_STAFF}")
    
    return test_smm_id in ALL_BOOKING_STAFF

def test_smm_booking_export():
    """Тест экспорта СММщика"""
    print("\n📊 Тестируем экспорт от СММщика...")
    
    # Пример данных заявки от СММщика
    smm_booking_data = {
        'name': 'Тест СММ Клиент',
        'phone': '+7900123456',
        'date': '2024-01-15',
        'time': '20:00',
        'guests': '4',
        'source': 'direct',  # Источник прямой
        'is_admin_booking': True  # СММщик создает админскую заявку
    }
    
    # Тестовый ID СММщика
    smm_user_id = 123456789  # Замените на реальный ID
    
    # Попробуем экспорт
    try:
        result = export_social_booking_to_sheets(smm_booking_data, smm_user_id)
        print(f"✅ Результат экспорта: {result}")
        return True
    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Тест конфигурации СММщиков")
    
    # Проверяем конфигурацию
    config_ok = test_smm_config()
    
    if config_ok:
        print("\n✅ Конфигурация СММщиков корректна")
        # Тестируем экспорт
        test_smm_booking_export()
    else:
        print("\n❌ Проблема с конфигурацией СММщиков!")
        print("💡 Проверьте переменную окружения SMM_IDS")
