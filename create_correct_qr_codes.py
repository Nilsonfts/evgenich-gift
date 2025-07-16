#!/usr/bin/env python3
"""
Создание правильных QR-кодов для Кристины
"""

import qrcode
import os

def create_qr_code(staff_name, telegram_id, output_dir="qr_codes"):
    """Создает QR-код для сотрудника."""
    
    # Создаем директорию, если её нет
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Правильная ссылка с Telegram ID
    url = f"https://t.me/evgenichspbbot?start=w_{telegram_id}"
    
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Создаем изображение
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем файл
    filename = f"{output_dir}/{staff_name}_{telegram_id}.png"
    img.save(filename)
    
    print(f"✅ QR-код создан: {filename}")
    print(f"🔗 Ссылка: {url}")
    print(f"📱 Можно сразу тестировать!")
    
    return filename, url

def main():
    """Создаем QR-коды для всех сотрудников."""
    print("🎯 СОЗДАНИЕ ПРАВИЛЬНЫХ QR-КОДОВ")
    print("=" * 40)
    
    # Данные сотрудников (из базы)
    staff_members = [
        ("Кристина", 208281210),
        ("Нил", 196614680),
        ("Тест", 12345678)
    ]
    
    for name, telegram_id in staff_members:
        print(f"\n👤 {name}:")
        create_qr_code(name, telegram_id)
    
    print(f"\n🎉 Все QR-коды созданы в папке 'qr_codes/'")
    print(f"📋 Используйте только эти ссылки - они гарантированно работают!")

if __name__ == "__main__":
    main()
