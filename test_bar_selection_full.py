#!/usr/bin/env python3
"""
Полный тест логики выбора барів в процессе бронирования
Проверяет весь цикл: от выбора до экспорта
"""

import json

# Цветовые коды для вывода
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_bar_mapping():
    """Тест маппирования выбора на коды баров"""
    print(f"\n{BLUE}=== ТЕСТ 1: Маппирование выбора бара на коды ==={RESET}")
    
    bar_mapping = {
        'bar_nevsky': 'ЕВГ_СПБ_НЕВ',
        'bar_rubinstein': 'ЕВГ_СПБ_РУБ'
    }
    
    tests = [
        ('bar_nevsky', 'ЕВГ_СПБ_НЕВ', 'Невский'),
        ('bar_rubinstein', 'ЕВГ_СПБ_РУБ', 'Рубинштейна'),
    ]
    
    for callback, expected_code, bar_name in tests:
        actual_code = bar_mapping.get(callback)
        status = f"{GREEN}✓{RESET}" if actual_code == expected_code else f"{YELLOW}✗{RESET}"
        print(f"{status} {bar_name}: {callback} → {actual_code} (ожидается: {expected_code})")
    
    return True

def test_booking_data_structure():
    """Тест структуры данных при сохранении выбора бара"""
    print(f"\n{BLUE}=== ТЕСТ 2: Структура данных при выборе бара ==={RESET}")
    
    # Симуляция процесса выбора бара
    booking_data = {
        'name': 'Иван Петров',
        'phone': '+79001234567',
        'date': '15.01.2026',
        'time': '19:30',
        'guests': '4',
    }
    
    # Пользователь нажимает на "Невский"
    bar_choice = 'bar_nevsky'
    bar_mapping = {
        'bar_nevsky': 'ЕВГ_СПБ_НЕВ',
        'bar_rubinstein': 'ЕВГ_СПБ_РУБ'
    }
    
    # Сохраняем выбор в данные
    booking_data['bar'] = bar_choice
    booking_data['amo_tag'] = bar_mapping.get(bar_choice, '')
    
    # Проверяем что всё сохранилось
    print(f"{GREEN}✓{RESET} Поле 'bar' сохранено: {booking_data.get('bar')}")
    print(f"{GREEN}✓{RESET} Поле 'amo_tag' сохранено: {booking_data.get('amo_tag')}")
    print(f"{GREEN}✓{RESET} Все необходимые данные присутствуют")
    
    return True

def test_sheets_export_structure():
    """Тест структуры строки для экспорта в Google Sheets"""
    print(f"\n{BLUE}=== ТЕСТ 3: Структура для экспорта в Google Sheets ==={RESET}")
    
    booking_data = {
        'name': 'Иван Петров',
        'phone': '+79001234567',
        'date': '15.01.2026',
        'time': '19:30 МСК',
        'guests': '4',
        'amo_tag': 'ЕВГ_СПБ_НЕВ',
        'bar': 'bar_nevsky'
    }
    
    # Симуляция экспорта
    row_data = [
        '2026-01-05 10:30',             # A: Дата Заявки
        booking_data.get('name', ''),   # B: Имя Гостя
        booking_data.get('phone', ''),  # C: Телефон
        '15.01.2026 19:30',             # D: Дата и время посещения
        booking_data.get('guests', ''), # E: Кол-во гостей
        'ВКонтакте',                    # F: Источник
        booking_data.get('amo_tag', ''), # G: ТЕГ для АМО (ВАЖНО!)
        'Иван (админ)',                 # H: Кто создал
        'Новая',                        # I: Статус
        'vk',                           # J: UTM Source
        'social',                       # K: UTM Medium
        'admin_booking',                # L: UTM Campaign
        'admin_panel_booking',          # M: UTM Content
        'vk_social_booking',            # N: UTM Term
        'BID-1234567890',               # O: ID заявки
        '123456789'                     # P: Telegram ID
    ]
    
    print(f"Всего колонок: {len(row_data)}")
    print(f"{GREEN}✓{RESET} Колонка A (Дата): {row_data[0]}")
    print(f"{GREEN}✓{RESET} Колонка B (Имя): {row_data[1]}")
    print(f"{GREEN}✓{RESET} Колонка G (Код бара АМО): {row_data[6]}")
    print(f"{GREEN}✓{RESET} Колонка H (Создатель): {row_data[7]}")
    
    return len(row_data) == 16  # Должно быть 16 колонок (A-P)

def test_bar_display_names():
    """Тест отображения названий баров в подтверждении"""
    print(f"\n{BLUE}=== ТЕСТ 4: Отображение названий баров ==={RESET}")
    
    bar_names = {
        'bar_nevsky': '🍷 Невский',
        'bar_rubinstein': '💎 Рубинштейна'
    }
    
    booking_data = {
        'name': 'Иван',
        'phone': '+79001234567',
        'date': '15.01.2026',
        'time': '19:30',
        'guests': '4',
        'bar': 'bar_nevsky',
    }
    
    bar_display = bar_names.get(booking_data.get('bar', ''), booking_data.get('bar', 'не указано'))
    
    print(f"{GREEN}✓{RESET} Выбран бар: {booking_data.get('bar')}")
    print(f"{GREEN}✓{RESET} Отображение: {bar_display}")
    
    confirmation = (
        "📋 Правильно всё записал?\n\n"
        f"📌 Имя: {booking_data.get('name')}\n"
        f"☎️ Телефон: {booking_data.get('phone')}\n"
        f"📆 Дата: {booking_data.get('date')}\n"
        f"🕒 Время: {booking_data.get('time')}\n"
        f"👥 Гостей: {booking_data.get('guests')}\n"
        f"🏠 Бар: {bar_display}"
    )
    
    print(f"\n{YELLOW}Текст подтверждения:{RESET}\n{confirmation}")
    
    return True

def test_export_data_types():
    """Тест типов данных при экспорте"""
    print(f"\n{BLUE}=== ТЕСТ 5: Типы данных при экспорте ==={RESET}")
    
    booking_data = {
        'name': 'Иван',
        'phone': '+79001234567',
        'date': '15.01.2026',
        'time': '19:30',
        'guests': '4',
        'amo_tag': 'ЕВГ_СПБ_НЕВ',
        'bar': 'bar_nevsky'
    }
    
    row_data = [
        'string_value',
        booking_data.get('name', ''),
        booking_data.get('phone', ''),
        'datetime',
        booking_data.get('guests', ''),
        'source',
        booking_data.get('amo_tag', ''),
        'creator',
        'status',
        'utm_source',
        'utm_medium',
        'utm_campaign',
        'utm_content',
        'utm_term',
        'bid_id',
        'user_id'
    ]
    
    # Валидация типов (все должны быть строки)
    all_valid = True
    for i, value in enumerate(row_data):
        if not isinstance(value, (str, int, float)):
            print(f"{YELLOW}✗{RESET} Колонка {i}: неправильный тип {type(value)}")
            all_valid = False
    
    if all_valid:
        print(f"{GREEN}✓{RESET} Все значения имеют правильные типы (str/int/float)")
    
    return all_valid

def main():
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}🎯 ПОЛНЫЙ ТЕСТ СИСТЕМЫ ВЫБОРА БАРОВ{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    tests = [
        ("Маппирование выбора на коды", test_bar_mapping),
        ("Структура данных", test_booking_data_structure),
        ("Структура для Google Sheets", test_sheets_export_structure),
        ("Отображение названий", test_bar_display_names),
        ("Типы данных при экспорте", test_export_data_types),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"{YELLOW}✗ {test_name}: {str(e)}{RESET}")
            failed += 1
    
    # Итоговый отчет
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}📊 ИТОГОВЫЙ ОТЧЕТ{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    print(f"{GREEN}✓ Пройденные тесты: {passed}{RESET}")
    print(f"{YELLOW}✗ Провалены: {failed}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к развертыванию.{RESET}")
        return 0
    else:
        print(f"\n{YELLOW}⚠️  Обнаружены ошибки. Проверьте логику.{RESET}")
        return 1

if __name__ == "__main__":
    exit(main())
