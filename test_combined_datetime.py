#!/usr/bin/env python3
"""
Демонстрация новой структуры колонок после объединения даты и времени
"""

def show_old_vs_new_structure():
    """Показывает разницу между старой и новой структурой колонок"""
    print("🔄 ИЗМЕНЕНИЕ СТРУКТУРЫ КОЛОНОК: Объединение даты и времени")
    print("=" * 70)
    
    print("❌ БЫЛО (18 колонок):")
    old_structure = [
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
        ("R", "Telegram ID создателя", "196614680")
    ]
    
    for letter, name, example in old_structure:
        print(f"  {letter}: {name:<25} | {example}")
    
    print(f"\nВсего колонок: {len(old_structure)}")
    
    print("\n✅ СТАЛО (17 колонок):")
    new_structure = [
        ("A", "Дата Заявки", "30.07.2025 14:30"),
        ("B", "Имя Гостя", "Иван Иванов"),
        ("C", "Телефон", "+7 (999) 123-45-67"),
        ("D", "Дата и время посещения", "31.07.2025 19:00 ✨"),
        ("E", "Кол-во гостей", "2"),
        ("F", "Источник", "ВКонтакте"),
        ("G", "ТЕГ для АМО", "vk"),
        ("H", "Повод Визита", "День рождения"),
        ("I", "Кто создал заявку", "@nilfts"),
        ("J", "Статус", "Новая"),
        ("K", "UTM Source", "vk"),
        ("L", "UTM Medium", "social"),
        ("M", "UTM Campaign", "admin_booking"),
        ("N", "UTM Content", "admin_panel_booking"),
        ("O", "UTM Term", "vk_social_booking"),
        ("P", "ID заявки", "BID-1722343800"),
        ("Q", "Telegram ID создателя", "196614680")
    ]
    
    for letter, name, example in new_structure:
        marker = " 🔄" if "посещения" in name else ""
        print(f"  {letter}: {name:<25} | {example}{marker}")
    
    print(f"\nВсего колонок: {len(new_structure)}")
    
    return True

def show_examples():
    """Показывает примеры объединенных данных"""
    print("\n📊 ПРИМЕРЫ ОБЪЕДИНЕННЫХ ДАННЫХ В КОЛОНКЕ D:")
    print("-" * 50)
    
    examples = [
        {
            "date": "31.07.2025",
            "time": "19:00",
            "combined": "31.07.2025 19:00",
            "description": "Стандартный случай"
        },
        {
            "date": "01.08.2025",
            "time": "20:30",
            "combined": "01.08.2025 20:30",
            "description": "Вечернее время"
        },
        {
            "date": "02.08.2025",
            "time": "",
            "combined": "02.08.2025",
            "description": "Только дата (время не указано)"
        },
        {
            "date": "завтра",
            "time": "18:00",
            "combined": "завтра 18:00",
            "description": "Относительная дата"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}:")
        print(f"   Дата: '{example['date']}'")
        print(f"   Время: '{example['time']}'")
        print(f"   → Колонка D: '{example['combined']}'")

def show_benefits():
    """Показывает преимущества объединения"""
    print("\n💡 ПРЕИМУЩЕСТВА ОБЪЕДИНЕНИЯ:")
    print("-" * 35)
    
    benefits = [
        "🎯 Экономия места - на одну колонку меньше",
        "👀 Лучшая читаемость - дата и время рядом",
        "📊 Упрощенная фильтрация по времени",
        "🔍 Удобный поиск по полному времени",
        "📱 Лучше отображается на мобильных устройствах",
        "⚡ Быстрее обработка данных"
    ]
    
    for benefit in benefits:
        print(f"  • {benefit}")

if __name__ == "__main__":
    print("🔧 ОБНОВЛЕНИЕ СТРУКТУРЫ ТАБЛИЦЫ")
    print("Объединение колонок D (Дата) и E (Время)")
    print()
    
    show_old_vs_new_structure()
    show_examples()
    show_benefits()
    
    print("\n" + "=" * 70)
    print("✅ ГОТОВО! Дата и время теперь объединены в колонку D")
    print("🎯 Telegram ID переехал из колонки R в колонку Q")
    print("📊 Общее количество колонок уменьшилось с 18 до 17")
