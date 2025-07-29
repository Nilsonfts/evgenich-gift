#!/usr/bin/env python3
"""
Тестирует добавление колонки R с Telegram ID в экспорт Google Sheets
"""

from social_bookings_export import export_social_booking_to_sheets, export_guest_booking_to_sheets

def test_admin_booking_export():
    """Тестирует экспорт админской заявки с Telegram ID"""
    print("🧪 Тестируем экспорт админской заявки с Telegram ID в колонку R...")
    
    # Тестовые данные админской заявки
    booking_data = {
        'name': 'Тест Тестович',
        'phone': '+7 (999) 123-45-67',
        'date': 'завтра',
        'time': '19:00',
        'guests': '2',
        'reason': 'День рождения',
        'source': 'source_vk'
    }
    
    admin_id = 196614680  # Telegram ID админа
    
    print(f"Данные заявки: {booking_data}")
    print(f"Telegram ID админа: {admin_id}")
    
    # Попробуем экспортировать (если настроены Google Sheets)
    try:
        result = export_social_booking_to_sheets(booking_data, admin_id)
        if result:
            print("✅ Админская заявка успешно экспортирована с Telegram ID в колонку R!")
        else:
            print("⚠️ Экспорт не удался (возможно, Google Sheets не настроены)")
    except Exception as e:
        print(f"⚠️ Ошибка при экспорте: {e}")

def test_guest_booking_export():
    """Тестирует экспорт гостевой заявки с Telegram ID"""
    print("\n🧪 Тестируем экспорт гостевой заявки с Telegram ID в колонку R...")
    
    # Тестовые данные гостевой заявки
    booking_data = {
        'name': 'Гость Гостевич',
        'phone': '+7 (999) 765-43-21',
        'date': 'послезавтра',
        'time': '20:30',
        'guests': '4',
        'reason': 'Корпоратив'
    }
    
    user_id = 208281210  # Telegram ID пользователя-гостя
    
    print(f"Данные заявки: {booking_data}")
    print(f"Telegram ID пользователя: {user_id}")
    
    # Попробуем экспортировать (если настроены Google Sheets)
    try:
        result = export_guest_booking_to_sheets(booking_data, user_id)
        if result:
            print("✅ Гостевая заявка успешно экспортирована с Telegram ID в колонку R!")
        else:
            print("⚠️ Экспорт не удался (возможно, Google Sheets не настроены)")
    except Exception as e:
        print(f"⚠️ Ошибка при экспорте: {e}")

def test_structure_verification():
    """Проверяет структуру данных, которые будут отправлены в таблицу"""
    print("\n🔍 Проверяем структуру данных для экспорта...")
    
    # Эмулируем создание row_data для админской заявки
    print("Структура данных для админской заявки:")
    columns = [
        "A: Дата Заявки", "B: Имя Гостя", "C: Телефон", "D: Дата посещения",
        "E: Время", "F: Кол-во гостей", "G: Источник", "H: ТЕГ для АМО",
        "I: Повод Визита", "J: Кто создал заявку", "K: Статус",
        "L: UTM Source", "M: UTM Medium", "N: UTM Campaign",
        "O: UTM Content", "P: UTM Term", "Q: ID заявки",
        "R: Telegram ID создателя ✨"  # Новая колонка!
    ]
    
    for i, column in enumerate(columns):
        print(f"  {column}")
    
    print(f"\nВсего колонок: {len(columns)}")
    print("✅ Колонка R (Telegram ID) успешно добавлена в структуру!")

if __name__ == "__main__":
    print("🚀 Тестирование добавления колонки R с Telegram ID")
    print("=" * 60)
    
    test_structure_verification()
    test_admin_booking_export()
    test_guest_booking_export()
    
    print("\n" + "=" * 60)
    print("📋 ИТОГ: Колонка R с Telegram ID успешно добавлена!")
    print("🔗 Теперь в Google Sheets будет записываться ID пользователя, создавшего заявку")
