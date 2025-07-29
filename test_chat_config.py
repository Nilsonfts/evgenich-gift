#!/usr/bin/env python3
"""
Тестирование конфигурации чатов для уведомлений.
"""

from config import (
    REPORT_CHAT_ID, 
    BOOKING_NOTIFICATIONS_CHAT_ID, 
    NASTOYKA_NOTIFICATIONS_CHAT_ID
)

def test_chat_configuration():
    """Проверяем правильность настройки чатов."""
    
    print("=== КОНФИГУРАЦИЯ ЧАТОВ ===")
    print(f"🔄 Старый чат (резерв): {REPORT_CHAT_ID}")
    print(f"📅 Чат для бронирований: {BOOKING_NOTIFICATIONS_CHAT_ID}")
    print(f"🥃 Чат для настоек: {NASTOYKA_NOTIFICATIONS_CHAT_ID}")
    
    print("\n=== НАЗНАЧЕНИЕ ЧАТОВ ===")
    print("📅 В чат для бронирований будут отправляться:")
    print("   • Новые заявки на бронирование столов")
    print("   • Подтверждения бронирований")
    
    print("\n🥃 В чат для настоек будут отправляться:")
    print("   • Запросы 'ЭЙ БЕДОЛАГА МЕНЕДЖЕР' по данным iiko")
    print("   • Ежедневные отчеты по купонам")
    print("   • Уведомления о QR-переходах сотрудников")
    
    print(f"\n🔄 Резервный чат используется для:")
    print("   • Проверки статуса сотрудников")
    print("   • Fallback при недоступности основных чатов")
    
    # Проверяем, что чаты разные
    if BOOKING_NOTIFICATIONS_CHAT_ID == NASTOYKA_NOTIFICATIONS_CHAT_ID:
        print("\n⚠️  ВНИМАНИЕ: Чаты для бронирований и настоек одинаковые!")
    else:
        print("\n✅ Чаты настроены правильно - используются разные для разных целей")

if __name__ == "__main__":
    test_chat_configuration()
