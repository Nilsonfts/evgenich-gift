#!/usr/bin/env python3
"""
Простой генератор QR-кодов с подписями
"""

import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3

def get_staff_from_db():
    """Получает список сотрудников из базы данных."""
    try:
        conn = sqlite3.connect("data/evgenich_data.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM staff WHERE status = 'active' ORDER BY full_name")
        staff_list = cur.fetchall()
        conn.close()
        
        return [dict(row) for row in staff_list]
    except Exception as e:
        print(f"❌ Ошибка получения данных: {e}")
        return []

def create_simple_qr_with_text(staff_member, output_dir="qr_branded"):
    """Создает простой QR-код с текстом снизу."""
    
    # Создаем директорию
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Данные
    full_name = staff_member['full_name']
    position = staff_member['position']
    unique_code = staff_member['unique_code']
    
    # Ссылка
    url = f"https://t.me/evgenichspbbot?start=w_{unique_code}"
    
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Создаем изображение QR-кода
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Размеры
    qr_width, qr_height = qr_img.size
    text_height = 100
    
    # Создаем финальное изображение
    final_width = qr_width
    final_height = qr_height + text_height
    final_img = Image.new('RGB', (final_width, final_height), 'white')
    
    # Вставляем QR-код
    final_img.paste(qr_img, (0, 0))
    
    # Добавляем текст
    draw = ImageDraw.Draw(final_img)
    
    # Используем стандартный шрифт
    try:
        font_name = ImageFont.truetype("arial.ttf", 24)
        font_pos = ImageFont.truetype("arial.ttf", 18)
    except:
        font_name = ImageFont.load_default()
        font_pos = ImageFont.load_default()
    
    # Позиция текста
    text_y = qr_height + 10
    
    # Имя (центрированно)
    text_width = len(full_name) * 14  # Приблизительно
    text_x = (final_width - text_width) // 2
    draw.text((text_x, text_y), full_name, fill="black", font=font_name)
    
    # Должность (центрированно)
    pos_text = f"({position})"
    pos_width = len(pos_text) * 10
    pos_x = (final_width - pos_width) // 2
    draw.text((pos_x, text_y + 30), pos_text, fill="gray", font=font_pos)
    
    # Код (центрированно)
    code_text = f"Код: {unique_code}"
    code_width = len(code_text) * 8
    code_x = (final_width - code_width) // 2
    draw.text((code_x, text_y + 55), code_text, fill="gray", font=font_pos)
    
    # Сохраняем
    filename = f"{output_dir}/{full_name.replace(' ', '_')}_QR.png"
    final_img.save(filename)
    
    return filename, url

def main():
    """Создаем простые QR-коды с подписями."""
    print("🎯 ПРОСТЫЕ QR-КОДЫ С ПОДПИСЯМИ")
    print("=" * 40)
    
    staff_list = get_staff_from_db()
    
    if not staff_list:
        print("❌ Нет сотрудников")
        return
    
    print(f"👥 Создаю QR-коды для {len(staff_list)} сотрудников:")
    print()
    
    for staff in staff_list:
        try:
            filename, url = create_simple_qr_with_text(staff)
            print(f"✅ {staff['full_name']}")
            print(f"   Файл: {filename}")
            print(f"   Ссылка: {url}")
            print()
            
        except Exception as e:
            print(f"❌ Ошибка для {staff['full_name']}: {e}")
    
    print("🎉 Готово! QR-коды с именами созданы в папке 'qr_branded/'")

if __name__ == "__main__":
    main()
