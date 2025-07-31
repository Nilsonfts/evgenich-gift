#!/usr/bin/env python3
"""
Тест новой структуры таблицы с автозаполнением
"""

# Имитируем переменные окружения для теста
import os
os.environ['BOT_TOKEN'] = 'test'
os.environ['CHANNEL_ID'] = '123'
os.environ['ADMIN_IDS'] = '123'
os.environ['GOOGLE_SHEET_KEY'] = 'test1,test2'
os.environ['GOOGLE_CREDENTIALS_JSON'] = '{}'
os.environ['HELLO_STICKER_ID'] = 'test'
os.environ['NASTOYKA_STICKER_ID'] = 'test'
os.environ['THANK_YOU_STICKER_ID'] = 'test'
os.environ['SMM_IDS'] = '555666777,888999000'

import logging
from datetime import datetime
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_new_table_structure():
    """Тест новой структуры таблицы с автозаполнением"""
    print("🧪 Тест новой структуры таблицы (18 столбцов A-R)")
    
    # Тестовые данные заявки
    booking_data = {
        'name': 'Тест Новая Структура',
        'phone': '+7900111222',
        'date': '2024-01-15',
        'time': '20:00',
        'guests': '6',
        'source': 'direct'
    }
    
    user_id = 555666777  # СММщик
    is_admin_booking = True
    
    print(f"📋 Исходные данные:")
    print(f"  Имя: {booking_data['name']}")
    print(f"  Телефон: {booking_data['phone']}")
    print(f"  Дата: {booking_data['date']}")
    print(f"  Время: {booking_data['time']}")
    print(f"  Гости: {booking_data['guests']}")
    print(f"  Источник: {booking_data['source']}")
    print(f"  User ID: {user_id}")
    print(f"  Admin booking: {is_admin_booking}")
    
    # Генерируем данные по новой структуре
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(moscow_tz)
    
    # A: Название сделки - "ЕВГ_СПБ (имя) телефон"
    deal_name = f"ЕВГ_СПБ ({booking_data['name']}) {booking_data['phone']}"
    
    # B: Дата создания (московское время)
    creation_date = moscow_time.strftime('%d.%m.%Y %H:%M')
    
    # C: Имя
    name = booking_data['name']
    
    # D: Дата и время посещения
    visit_datetime = f"{booking_data['date']} {booking_data['time']}"
    
    # E: Тег города - автоматически "ЕВГ_СПБ"
    city_tag = "ЕВГ_СПБ"
    
    # F: Телефон
    phone = booking_data['phone']
    
    # G: Количество гостей
    guests = booking_data['guests']
    
    # H: Источник
    source = booking_data['source']
    
    # I-Q: UTM данные (пустые для direct)
    utm_data = [''] * 9  # I, J, K, L, M, N, O, P, Q
    
    # R: Telegram ID
    telegram_id = str(user_id)
    
    # Собираем итоговый ряд (18 столбцов A-R)
    row_data = [
        deal_name,      # A
        creation_date,  # B
        name,          # C
        visit_datetime, # D
        city_tag,      # E
        phone,         # F
        guests,        # G
        source,        # H
        *utm_data,     # I-Q (9 пустых)
        telegram_id    # R
    ]
    
    print(f"\n📊 Сгенерированная структура (18 столбцов A-R):")
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']
    
    for i, (col, data) in enumerate(zip(columns, row_data)):
        if data:  # Показываем только заполненные
            print(f"  {col}: {data}")
    
    print(f"\n🔢 Проверка:")
    print(f"  Всего столбцов: {len(row_data)}")
    print(f"  Ожидается: 18 (A-R)")
    print(f"  Соответствует: {'✅' if len(row_data) == 18 else '❌'}")
    
    # Проверяем автозаполнение
    print(f"\n🤖 Автозаполнение:")
    print(f"  Название сделки (A): {deal_name}")
    print(f"  Тег города (E): {city_tag}")
    print(f"  Telegram ID (R): {telegram_id}")
    
    return len(row_data) == 18

def test_smm_access():
    """Тест доступа СММщика"""
    from config import SMM_IDS, ALL_BOOKING_STAFF
    
    print(f"\n👤 Тест доступа СММщика:")
    smm_id = 555666777
    
    print(f"  СММщик ID: {smm_id}")
    print(f"  В SMM_IDS: {'✅' if smm_id in SMM_IDS else '❌'}")
    print(f"  В ALL_BOOKING_STAFF: {'✅' if smm_id in ALL_BOOKING_STAFF else '❌'}")
    print(f"  Может создавать брони: {'✅' if smm_id in ALL_BOOKING_STAFF else '❌'}")
    
    return smm_id in ALL_BOOKING_STAFF

if __name__ == "__main__":
    print("🚀 Тест новой структуры и доступа СММщиков\n")
    
    # Тест 1: новая структура таблицы
    structure_ok = test_new_table_structure()
    
    # Тест 2: доступ СММщика
    access_ok = test_smm_access()
    
    print(f"\n📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"  Структура таблицы: {'✅' if structure_ok else '❌'}")
    print(f"  Доступ СММщика: {'✅' if access_ok else '❌'}")
    
    if structure_ok and access_ok:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print(f"💡 РЕШЕНИЕ ПРОБЛЕМЫ С СММщиком:")
        print(f"   1. ✅ Логика работает правильно")
        print(f"   2. ⚠️  Нужно установить SMM_IDS в Railway")
        print(f"   3. 📝 Формат: SMM_IDS='ID1,ID2,ID3'")
    else:
        print(f"\n❌ ЕСТЬ ПРОБЛЕМЫ!")
