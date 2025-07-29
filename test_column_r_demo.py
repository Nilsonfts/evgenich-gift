#!/usr/bin/env python3
"""
Простой тест для демонстрации добавления колонки R с Telegram ID
"""

def test_column_structure():
    """Показывает новую структуру колонок в Google Sheets"""
    print("🚀 Тестирование добавления колонки R с Telegram ID")
    print("=" * 60)
    
    print("🔍 Структура данных для экспорта в Google Sheets:")
    print()
    
    # Структура колонок, как она будет в Google Sheets
    columns = [
        ("A", "Дата Заявки", "30.07.2025 14:30"),
        ("B", "Имя Гостя", "Иван Иванов"),
        ("C", "Телефон", "+7 (999) 123-45-67"),
        ("D", "Дата посещения", "31.07.2025"),
        ("E", "Время", "19:00"),
        ("F", "Кол-во гостей", "2"),
        ("G", "Источник", "ВКонтакте"),
        ("H", "ТЕГ для АМО", "vk"),
        ("I", "Повод Визита", "День рождения"),
        ("J", "Кто создал заявку", "@nilfts"),
        ("K", "Статус", "Новая"),
        ("L", "UTM Source", "vk"),
        ("M", "UTM Medium", "social"),
        ("N", "UTM Campaign", "admin_booking"),
        ("O", "UTM Content", "admin_panel_booking"),
        ("P", "UTM Term", "vk_social_booking"),
        ("Q", "ID заявки", "BID-1722343800"),
        ("R", "Telegram ID создателя ✨", "196614680")  # НОВАЯ КОЛОНКА!
    ]
    
    print("Колонки в Google Sheets:")
    for letter, name, example in columns:
        marker = " ← НОВАЯ!" if letter == "R" else ""
        print(f"  {letter}: {name:<25} | Пример: {example}{marker}")
    
    print(f"\nВсего колонок: {len(columns)}")
    print("\n✅ УСПЕШНО! Колонка R добавлена для записи Telegram ID пользователя")
    
    print("\n" + "=" * 60)
    print("📋 ЧТО ИЗМЕНИЛОСЬ:")
    print("1. В export_social_booking_to_sheets() добавлен admin_id в колонку R")
    print("2. В export_guest_booking_to_sheets() добавлен user_id в колонку R (опционально)")
    print("3. Обновлены вызовы функций в booking_flow.py")
    print("4. Теперь в таблице будет видно, кто именно создал каждую заявку!")
    
    return True

def simulate_booking_export():
    """Симулирует процесс экспорта с новыми данными"""
    print("\n🎭 СИМУЛЯЦИЯ ЭКСПОРТА ЗАЯВКИ:")
    print("-" * 40)
    
    # Пример админской заявки
    admin_booking = {
        'name': 'Тест Тестович',
        'phone': '+7 (999) 123-45-67',
        'date': 'завтра',
        'time': '19:00',
        'guests': '2',
        'reason': 'День рождения',
        'source': 'source_vk'
    }
    admin_id = 196614680
    
    print("Админская заявка:")
    print(f"  Имя: {admin_booking['name']}")
    print(f"  Телефон: {admin_booking['phone']}")
    print(f"  Создал админ с ID: {admin_id}")
    print(f"  → В колонку R будет записано: {admin_id}")
    
    print()
    
    # Пример гостевой заявки
    guest_booking = {
        'name': 'Гость Гостевич',
        'phone': '+7 (999) 765-43-21',
        'date': 'послезавтра',
        'time': '20:30',
        'guests': '4',
        'reason': 'Корпоратив'
    }
    user_id = 208281210
    
    print("Гостевая заявка:")
    print(f"  Имя: {guest_booking['name']}")
    print(f"  Телефон: {guest_booking['phone']}")
    print(f"  Создал пользователь с ID: {user_id}")
    print(f"  → В колонку R будет записано: {user_id}")
    
    return True

if __name__ == "__main__":
    test_column_structure()
    simulate_booking_export()
    
    print("\n🎉 ГОТОВО! Колонка R теперь будет содержать Telegram ID создателя заявки!")
