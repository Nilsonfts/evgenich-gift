#!/usr/bin/env python3
"""
Тестирование новой системы источников трафика и экспорта в Google Sheets
"""

from social_bookings_export import parse_booking_date

def test_new_sources():
    """Тестируем новые источники трафика."""
    
    print("🧪 ТЕСТИРОВАНИЕ НОВОЙ СИСТЕМЫ ИСТОЧНИКОВ ТРАФИКА\n")
    
    print("Источники трафика:")
    print("• source_vk -> ВКонтакте (тег АМО: vk)")
    print("• source_inst -> Instagram (тег АМО: inst)")
    print("• source_bot_tg -> Бот в ТГ (тег АМО: bot_tg)")
    print("• source_tg -> ТГ-канал (тег АМО: tg)")
    print()
    
    print("Структура таблицы:")
    print("A: Дата Заявки | B: Имя Гостя | C: Телефон | D: Дата посещения")
    print("E: Время | F: Кол-во гостей | G: Источник | H: ТЕГ для АМО")
    print("I: Повод Визита | J: Кто создал заявку | K: Статус")
    print("=" * 50)
    
    # Тестовые данные для каждого источника
    test_bookings = [
        {
            'name': 'Нил Тест',
            'phone': '89996106215',
            'date': 'завтра',
            'time': '19:30',
            'guests': '5',
            'source': 'source_vk',  # ВКонтакте -> vk
            'reason': 'чисто для кайфа'
        },
        {
            'name': 'Нил Тест 2',
            'phone': '89996106215',
            'date': '30 июля',
            'time': '20:30',
            'guests': '5',
            'source': 'source_inst',  # Instagram -> inst
            'reason': 'Просто так'
        },
        {
            'name': 'Нил Тест 3',
            'phone': '89996106215',
            'date': '01.08',
            'time': '21:00',
            'guests': '3',
            'source': 'source_bot_tg',  # Бот в ТГ -> bot_tg
            'reason': 'День рождения'
        },
        {
            'name': 'Нил Тест 4',
            'phone': '89996106215',
            'date': 'в субботу',
            'time': '18:00',
            'guests': '4',
            'source': 'source_tg',  # ТГ-канал -> tg
            'reason': 'Встреча с друзьями'
        }
    ]
    
    for i, booking in enumerate(test_bookings, 1):
        print(f"\n🔄 Тест {i}: {booking['source']}")
        print(f"📅 Дата: {booking['date']} -> {parse_booking_date(booking['date'])}")
        
        # Показываем что будет отправлено в таблицу
        print(f"📊 Будет отправлено в таблицу:")
        print(f"   G (Источник): {get_source_display(booking['source'])}")
        print(f"   H (ТЕГ АМО): {get_amo_tag(booking['source'])}")

def get_source_display(source_key):
    """Получить отображаемое название источника."""
    mapping = {
        'source_vk': 'ВКонтакте',
        'source_inst': 'Instagram', 
        'source_bot_tg': 'Бот в ТГ',
        'source_tg': 'ТГ-канал'
    }
    return mapping.get(source_key, source_key)

def get_amo_tag(source_key):
    """Получить тег для АМО."""
    mapping = {
        'source_vk': 'vk',
        'source_inst': 'inst', 
        'source_bot_tg': 'bot_tg',
        'source_tg': 'tg'
    }
    return mapping.get(source_key, 'unknown')

if __name__ == "__main__":
    test_new_sources()
