#!/usr/bin/env python3
"""
Добавляем текст к уже созданным QR-кодам
"""

import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3

def add_text_to_qr():
    """Добавляет текст к простым QR-кодам."""
    print("🎯 ДОБАВЛЕНИЕ ТЕКСТА К QR-КОДАМ")
    print("=" * 35)
    
    # Получаем сотрудников
    try:
        conn = sqlite3.connect("data/evgenich_data.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM staff WHERE status = 'active'")
        staff_list = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return
    
    input_dir = "final_qr_codes"
    output_dir = "branded_qr_codes"
    os.makedirs(output_dir, exist_ok=True)
    
    for staff in staff_list:
        name = staff['full_name']
        position = staff['position']
        code = staff['unique_code']
        
        # Файл простого QR
        simple_qr_file = f"{input_dir}/{name.replace(' ', '_')}_simple_qr.png"
        
        if not os.path.exists(simple_qr_file):
            print(f"❌ Файл не найден: {simple_qr_file}")
            continue
            
        print(f"\n👤 Обрабатываю: {name}")
        
        try:
            # Загружаем простой QR
            qr_img = Image.open(simple_qr_file)
            qr_width, qr_height = qr_img.size
            
            # Создаем новое изображение с дополнительным местом для текста
            text_space = 80
            final_width = qr_width
            final_height = qr_height + text_space
            
            # Белый фон
            final_img = Image.new('RGB', (final_width, final_height), 'white')
            
            # Вставляем QR в верхнюю часть
            final_img.paste(qr_img, (0, 0))
            
            # Создаем текстовую область
            draw = ImageDraw.Draw(final_img)
            
            # Позиции для текста
            text_start_y = qr_height + 10
            
            # Имя сотрудника
            name_y = text_start_y
            draw.text((10, name_y), name, fill="black")
            
            # Должность
            position_y = text_start_y + 25
            draw.text((10, position_y), f"({position})", fill="gray")
            
            # ID для справки
            id_y = text_start_y + 50
            draw.text((10, id_y), f"ID: {code}", fill="lightgray")
            
            # Сохраняем
            output_file = f"{output_dir}/{name.replace(' ', '_')}_branded.png"
            final_img.save(output_file)
            
            print(f"✅ Создан: {output_file}")
            
        except Exception as e:
            print(f"❌ Ошибка обработки {name}: {e}")
    
    print(f"\n🎉 Готово! QR-коды с текстом в папке: {output_dir}/")
    print("🖨️ Готовы к печати!")

if __name__ == "__main__":
    add_text_to_qr()
