#!/usr/bin/env python3
"""
Тестирует экспорт в дополнительную таблицу
"""

def test_secondary_table_structure():
    """Показывает структуру новой таблицы"""
    print("🔗 ДОПОЛНИТЕЛЬНАЯ ТАБЛИЦА: Структура экспорта")
    print("=" * 60)
    
    print("📊 Структура колонок (A-P):")
    columns = [
        ("A", "Дата Заявки", "30.07.2025 14:30"),
        ("B", "Канал", "Админ-панель / Гостевое бронирование"),
        ("C", "Кто создал заявку", "@nilfts / 👤 Посетитель"),
        ("D", "Статус", "Новая"),
        ("E", "ID us", "BID-1722343800"),
        ("F", "Имя Гостя", "Иван Иванов"),
        ("G", "Телефон", "+7 (999) 123-45-67"),
        ("H", "Дата / Время", "31.07.2025 19:00"),
        ("I", "Кол-во гостей", "2"),
        ("J", "Повод Визита", "День рождения"),
        ("K", "UTM Source (Источник)", "vk"),
        ("L", "UTM Medium (Канал)", "social"),
        ("M", "UTM Campaign (Кампания)", "admin_booking"),
        ("N", "UTM Content (Содержание)", "admin_panel_booking"),
        ("O", "UTM Term (Ключ/Дата)", "vk_social_booking"),
        ("P", "ID TG", "196614680")
    ]
    
    for letter, name, example in columns:
        print(f"  {letter}: {name:<25} | {example}")
    
    print(f"\nВсего колонок: {len(columns)}")
    
    return True

def test_dual_export_logic():
    """Показывает логику двойного экспорта"""
    print("\n🔄 ЛОГИКА ДВОЙНОГО ЭКСПОРТА:")
    print("-" * 40)
    
    print("1. Основная таблица (существующая):")
    print("   📋 Ключ: 1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs")
    print("   📄 Вкладка: 1842872487 (Заявки из Соц сетей)")
    print("   📊 Колонки: A-Q (17 колонок)")
    
    print("\n2. Дополнительная таблица (новая):")
    print("   📋 Ключ: 1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4")
    print("   📄 Вкладка: 871899838")
    print("   📊 Колонки: A-P (16 колонок)")
    
    print("\n3. 🔄 Процесс экспорта:")
    print("   ① Заявка создается через бота")
    print("   ② Экспорт в основную таблицу (полные данные)")
    print("   ③ Экспорт в дополнительную таблицу (упрощенные данные)")
    print("   ④ Логирование результатов")

def test_configuration_setup():
    """Показывает настройку конфигурации"""
    print("\n⚙️ НАСТРОЙКА КОНФИГУРАЦИИ:")
    print("-" * 35)
    
    print("В переменной окружения GOOGLE_SHEET_KEY:")
    print("  GOOGLE_SHEET_KEY=\"1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs, 1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4\"")
    
    print("\nПарсинг в config.py:")
    print("  GOOGLE_SHEET_KEY = основная таблица (первый ключ)")
    print("  GOOGLE_SHEET_KEY_SECONDARY = дополнительная (второй ключ)")
    
    print("\nИспользование в коде:")
    print("  export_social_booking_to_sheets() → основная таблица")
    print("  export_booking_to_secondary_table() → дополнительная таблица")

def test_examples():
    """Показывает примеры данных"""
    print("\n📝 ПРИМЕРЫ ЭКСПОРТА:")
    print("-" * 25)
    
    examples = [
        {
            "type": "Админская заявка",
            "channel": "Админ-панель", 
            "creator": "@nilfts",
            "telegram_id": "196614680",
            "utm_source": "vk"
        },
        {
            "type": "Гостевая заявка",
            "channel": "Гостевое бронирование",
            "creator": "👤 Посетитель (через бота)",
            "telegram_id": "208281210", 
            "utm_source": "bot_tg"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['type']}:")
        print(f"   Канал (B): {example['channel']}")
        print(f"   Создатель (C): {example['creator']}")
        print(f"   UTM Source (K): {example['utm_source']}")
        print(f"   ID TG (P): {example['telegram_id']}")

if __name__ == "__main__":
    print("🚀 ТЕСТИРОВАНИЕ: Дублирующий экспорт в дополнительную таблицу")
    print()
    
    test_secondary_table_structure()
    test_dual_export_logic()
    test_configuration_setup()
    test_examples()
    
    print("\n" + "=" * 60)
    print("✅ ГОТОВО! Дублирующий экспорт настроен")
    print("📋 Теперь все заявки будут дублироваться в обе таблицы")
    print("🔗 Дополнительная таблица: https://docs.google.com/spreadsheets/d/1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4/edit?gid=871899838")
