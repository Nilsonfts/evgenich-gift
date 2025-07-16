#!/usr/bin/env python3
"""
Генератор QR-кодов без проблемных методов PIL
"""

import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3

def create_qr_final():
    """Создает QR-коды для всех сотрудников с текстом."""
    print("🎯 ФИНАЛЬНОЕ СОЗДАНИЕ QR-КОДОВ")
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
    
    # Папка для файлов
    output_dir = "final_qr_codes"
    os.makedirs(output_dir, exist_ok=True)
    
    for staff in staff_list:
        name = staff['full_name']
        position = staff['position']
        code = staff['unique_code']
        
        print(f"\n👤 {name} (ID: {code})")
        
        # URL
        url = f"https://t.me/evgenichspbbot?start=w_{code}"
        
        try:
            # Создаем QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Генерируем изображение QR
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_width, qr_height = qr_img.size
            
            # Создаем финальное изображение с местом под текст
            text_height = 60
            final_img = Image.new('RGB', (qr_width, qr_height + text_height), 'white')
            
            # Вставляем QR в верхнюю часть
            final_img.paste(qr_img, (0, 0))
            
            # Работаем с текстом
            draw = ImageDraw.Draw(final_img)
            
            # Используем стандартный шрифт или создаем простой текст
            try:
                # Пытаемся использовать системный шрифт
                font = ImageFont.load_default()
            except:
                font = None
            
            # Позиция для текста (под QR-кодом)
            text_y = qr_height + 10
            
            # Рисуем имя (жирно)
            name_text = name
            if font:
                # Подсчитываем примерную ширину для центрирования
                name_width = len(name_text) * 6  # примерно 6 пикселей на символ
                name_x = max(0, (qr_width - name_width) // 2)
                draw.text((name_x, text_y), name_text, fill="black", font=font)
            else:
                # Без шрифта
                name_x = max(0, (qr_width - len(name_text) * 6) // 2)
                draw.text((name_x, text_y), name_text, fill="black")
            
            # Рисуем должность
            pos_text = f"({position})"
            if font:
                pos_width = len(pos_text) * 5
                pos_x = max(0, (qr_width - pos_width) // 2)
                draw.text((pos_x, text_y + 20), pos_text, fill="gray", font=font)
            else:
                pos_x = max(0, (qr_width - len(pos_text) * 5) // 2)
                draw.text((pos_x, text_y + 20), pos_text, fill="gray")
            
            # Сохраняем
            filename = f"{output_dir}/{name.replace(' ', '_').replace('/', '_')}_qr.png"
            final_img.save(filename)
            
            print(f"✅ Файл: {filename}")
            print(f"🔗 {url}")
            
        except Exception as e:
            print(f"❌ Ошибка создания QR: {e}")
            # Создаем простой QR без текста
            try:
                simple_qr = qr.make_image(fill_color="black", back_color="white")
                filename = f"{output_dir}/{name.replace(' ', '_')}_simple_qr.png"
                simple_qr.save(filename)
                print(f"💾 Простой QR: {filename}")
            except Exception as e2:
                print(f"❌ И простой QR не создался: {e2}")
    
    print(f"\n🎉 Готово! Проверьте папку: {output_dir}/")

if __name__ == "__main__":
    create_qr_final()
