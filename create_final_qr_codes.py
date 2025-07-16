#!/usr/bin/env python3
"""
Простое создание QR-кодов с текстовыми файлами подписей
"""

import qrcode
import sqlite3
import os

def create_simple_qr_with_info():
    """Создает простые QR-коды и текстовые файлы с информацией."""
    
    output_dir = "qr_codes_final"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("🎯 СОЗДАНИЕ ФИНАЛЬНЫХ QR-КОДОВ")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect("data/evgenich_data.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM staff WHERE status = 'active' ORDER BY full_name")
        staff_list = cur.fetchall()
        
        if not staff_list:
            print("❌ Нет активных сотрудников")
            return
        
        print(f"👥 Создаю QR-коды для {len(staff_list)} сотрудников:")
        print()
        
        for i, staff in enumerate(staff_list, 1):
            name = staff['full_name']
            telegram_id = staff['telegram_id']
            position = staff['position']
            
            # URL для QR-кода
            url = f"https://t.me/evgenichspbbot?start=w_{telegram_id}"
            
            print(f"{i}. {name} ({position})")
            print(f"   ID: {telegram_id}")
            print(f"   URL: {url}")
            
            # Создаем QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Сохраняем QR-код
            img = qr.make_image(fill_color="black", back_color="white")
            qr_filename = f"{output_dir}/{name}_{telegram_id}.png"
            img.save(qr_filename)
            print(f"   ✅ QR: {qr_filename}")
            
            # Создаем текстовый файл с информацией
            info_filename = f"{output_dir}/{name}_{telegram_id}_info.txt"
            with open(info_filename, 'w', encoding='utf-8') as f:
                f.write(f"СОТРУДНИК: {name}\n")
                f.write(f"ДОЛЖНОСТЬ: {position}\n")
                f.write(f"TELEGRAM ID: {telegram_id}\n")
                f.write(f"QR-КОД ССЫЛКА: {url}\n")
                f.write(f"\n")
                f.write(f"ИНСТРУКЦИЯ:\n")
                f.write(f"1. Распечатайте QR-код\n")
                f.write(f"2. Подпишите: {name} ({position})\n")
                f.write(f"3. Разместите в рабочей зоне сотрудника\n")
                f.write(f"4. Все переходы будут отслеживаться как 'staff'\n")
            
            print(f"   ✅ Инфо: {info_filename}")
            print()
        
        # Создаем сводный файл
        summary_file = f"{output_dir}/SUMMARY_ALL_QR_CODES.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("🎯 СВОДКА ПО QR-КОДАМ СОТРУДНИКОВ\n")
            f.write("=" * 50 + "\n\n")
            
            for staff in staff_list:
                name = staff['full_name']
                telegram_id = staff['telegram_id']
                position = staff['position']
                url = f"https://t.me/evgenichspbbot?start=w_{telegram_id}"
                
                f.write(f"• {name} ({position})\n")
                f.write(f"  Telegram ID: {telegram_id}\n")
                f.write(f"  QR-ссылка: {url}\n")
                f.write(f"  Файл QR: {name}_{telegram_id}.png\n")
                f.write(f"\n")
            
            f.write("\n📋 ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ:\n")
            f.write("1. Распечатайте QR-коды\n")
            f.write("2. Подпишите каждый именем сотрудника\n")
            f.write("3. Раздайте сотрудникам или разместите в их зонах\n")
            f.write("4. Все переходы будут отслеживаться в отчетах\n")
            f.write("\n✅ НИКАКОЙ КИРИЛЛИЦЫ В URL - ВСЁ РАБОТАЕТ!\n")
        
        conn.close()
        
        print("🎉 ВСЁ ГОТОВО!")
        print(f"📁 Все файлы в папке: {output_dir}/")
        print("📋 Сводка: SUMMARY_ALL_QR_CODES.txt")
        print("🖨️ Готово к печати и использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    create_simple_qr_with_info()
