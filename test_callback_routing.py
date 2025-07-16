#!/usr/bin/env python3
"""
Тест для проверки правильности обработки callback-запросов админ-панели
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Имитируем структуру callback-запросов
test_callbacks = [
    "admin_menu_reports",
    "admin_menu_promotions", 
    "admin_menu_content",
    "admin_menu_data",
    "admin_main_menu",
    "boss_toggle_promotions",
    "check_subscription",  # Не админский
    "menu_nastoiki_main",  # Не админский
    "main_menu_choice"     # Не админский
]

def test_callback_routing():
    """Тестирует правильность маршрутизации callback-запросов."""
    print("🧪 ТЕСТ МАРШРУТИЗАЦИИ CALLBACK-ЗАПРОСОВ")
    print("=" * 50)
    
    # Имитируем логику из callback_query.py
    def should_handle_in_callback_query(call_data):
        return not (call_data.startswith('admin_') or call_data.startswith('boss_'))
    
    # Имитируем логику из admin_panel.py
    def should_handle_in_admin_panel(call_data):
        return call_data.startswith('admin_') or call_data.startswith('boss_')
    
    print("📋 Результаты маршрутизации:")
    for callback in test_callbacks:
        in_callback_query = should_handle_in_callback_query(callback)
        in_admin_panel = should_handle_in_admin_panel(callback)
        
        if in_callback_query and in_admin_panel:
            status = "❌ КОНФЛИКТ"
        elif in_callback_query:
            status = "✅ callback_query.py"
        elif in_admin_panel:
            status = "✅ admin_panel.py"
        else:
            status = "⚠️ НЕ ОБРАБОТАЕТСЯ"
        
        print(f"  • {callback:<25} → {status}")
    
    print("\n" + "=" * 50)
    
    # Проверяем админские callback-запросы
    admin_callbacks = [cb for cb in test_callbacks if cb.startswith('admin_') or cb.startswith('boss_')]
    non_admin_callbacks = [cb for cb in test_callbacks if not (cb.startswith('admin_') or cb.startswith('boss_'))]
    
    print(f"📊 Статистика:")
    print(f"  • Админские callback-запросы: {len(admin_callbacks)}")
    print(f"  • Обычные callback-запросы: {len(non_admin_callbacks)}")
    
    conflicts = 0
    for callback in test_callbacks:
        if should_handle_in_callback_query(callback) and should_handle_in_admin_panel(callback):
            conflicts += 1
    
    if conflicts == 0:
        print(f"  • Конфликтов: {conflicts} ✅")
        print("\n🎉 Все callback-запросы будут обработаны корректно!")
    else:
        print(f"  • Конфликтов: {conflicts} ❌")
        print("\n💥 Обнаружены конфликты в маршрутизации!")
    
    return conflicts == 0

if __name__ == "__main__":
    test_callback_routing()
