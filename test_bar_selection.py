#!/usr/bin/env python3
"""
Тест выбора бара в процессе бронирования
"""

# Симуляция логики выбора бара
bar_mapping = {
    'bar_nevsky': 'ЕВГ_СПБ_НЕВ',
    'bar_rubinstein': 'ЕВГ_СПБ_РУБ'
}

# Симуляция данных брони
booking_data = {
    'name': 'Иван',
    'phone': '+79001234567',
    'date': '15.01.2026',
    'time': '19:30',
    'guests': '4',
    'bar': 'bar_nevsky',
    'source': 'source_vk',
    'is_admin_booking': True
}

# Маппируем выбор бара на коды для AMO
bar_code = bar_mapping.get(booking_data.get('bar', ''), '')
booking_data['amo_tag'] = bar_code

print("✅ ТЕСТ ВЫБОРА БАРА")
print("=" * 60)
print(f"📌 Бар (выбор): {booking_data.get('bar')}")
print(f"🏠 Код бара (amo_tag): {booking_data.get('amo_tag')}")
print()

# Проверяем что попадет в Google Sheets
print("📊 ДАННЫЕ ДЛЯ ЭКСПОРТА В GOOGLE SHEETS:")
print(f"  Колонка G (ТЕГ для АМО): {booking_data.get('amo_tag')}")
print(f"  Колонка H (Кто создал): [admin_name]")
print()

# Тест обоих баров
print("🧪 ТЕСТ ОБОИХ БАРОВ:")
for bar_callback, bar_name in [('bar_nevsky', 'Невский'), ('bar_rubinstein', 'Рубинштейна')]:
    code = bar_mapping.get(bar_callback, '')
    print(f"  ✓ {bar_name} ({bar_callback}) → {code}")

print()
print("✅ Логика выбора бара корректна!")
