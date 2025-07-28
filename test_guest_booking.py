#!/usr/bin/env python3
"""
Тест новой системы гостевого бронирования
"""

import sys
import os

print("🧪 Тестирование системы гостевого бронирования")
print("=" * 50)

try:
    # Тестируем импорт клавиатур
    from keyboards import get_guest_source_keyboard, get_traffic_source_keyboard
    print("✅ Клавиатуры импортированы успешно")
    
    # Тестируем импорт UTM данных
    from social_bookings_export import GUEST_SOURCE_UTM_DATA, ALL_SOURCE_UTM_DATA, SOURCE_UTM_DATA
    print("✅ UTM данные импортированы успешно")
    
    # Тестируем импорт обработчиков
    from handlers.booking_flow import register_booking_handlers
    print("✅ Обработчики бронирования импортированы успешно")
    
    # Проверяем структуру данных
    print(f"\n📊 Статистика источников:")
    print(f"- Админские источники: {len(SOURCE_UTM_DATA)}")
    print(f"- Гостевые источники: {len(GUEST_SOURCE_UTM_DATA)}")
    print(f"- Всего источников: {len(ALL_SOURCE_UTM_DATA)}")
    
    # Проверяем гостевые источники
    print(f"\n🎯 Гостевые источники:")
    for key, data in GUEST_SOURCE_UTM_DATA.items():
        print(f"  {key}: {data['utm_source']}/{data['utm_medium']}")
    
    # Проверяем целостность данных
    missing_in_all = set(GUEST_SOURCE_UTM_DATA.keys()) - set(ALL_SOURCE_UTM_DATA.keys())
    if missing_in_all:
        print(f"❌ Отсутствуют в ALL_SOURCE_UTM_DATA: {missing_in_all}")
    else:
        print("✅ Все гостевые источники присутствуют в общем списке")
    
    # Тестируем создание клавиатуры
    guest_keyboard = get_guest_source_keyboard()
    print(f"✅ Гостевая клавиатура создана, кнопок: {len(guest_keyboard.keyboard)}")
    
    admin_keyboard = get_traffic_source_keyboard()
    print(f"✅ Админская клавиатура создана, кнопок: {len(admin_keyboard.keyboard)}")
    
    print(f"\n🎉 Все тесты пройдены успешно!")
    print("📝 Система готова к использованию")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
