#!/usr/bin/env python3
"""
Максимально простой генератор QR-кодов с текстом
"""

import qrcode
from PIL import Image, ImageDraw
import os
import sqlite3

def create_qr_with_label():
    """Создает QR-коды для всех сотрудников."""
    print("🎯 СОЗДАНИЕ QR-КОДОВ С ПОДПИСЯМИ")
    print("=" * 45)
    
    # Получаем данные из базы
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
    
    # Создаем папку
    output_dir = "qr_with_labels"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for staff in staff_list:
        name = staff['full_name']
        position = staff['position']
        code = staff['unique_code']
        
        print(f"\n👤 Создаю QR для: {name}")
        
        # Ссылка
        url = f"https://t.me/evgenichspbbot?start=w_{code}"
        
        try:
            # QR-код
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Размеры
            qr_size = qr_img.size[0]
            
            # Новое изображение с местом для текста
            total_height = qr_size + 80
            final_img = Image.new('RGB', (qr_size, total_height), 'white')
            
            # Вставляем QR
            final_img.paste(qr_img, (0, 0))
            
            # Добавляем текст простым способом
            draw = ImageDraw.Draw(final_img)
            
            # Текст без шрифтов (используем стандартный)
            y_pos = qr_size + 10
            
            # Примерное центрирование
            name_x = max(5, (qr_size - len(name) * 6) // 2)
            pos_x = max(5, (qr_size - len(f"({position})") * 5) // 2)
            code_x = max(5, (qr_size - len(f"ID: {code}") * 5) // 2)
            
            # Рисуем текст
            draw.text((name_x, y_pos), name, fill="black")
            draw.text((pos_x, y_pos + 20), f"({position})", fill="gray")
            draw.text((code_x, y_pos + 40), f"ID: {code}", fill="gray")
            
            # Сохраняем
            filename = f"{output_dir}/{name.replace(' ', '_')}_QR.png"
            final_img.save(filename)
            
            print(f"✅ Создан: {filename}")
            print(f"🔗 Ссылка: {url}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print(f"\n🎉 QR-коды созданы в папке '{output_dir}/'")
    print("🖨️ Готовы к печати с именами сотрудников!")

if __name__ == "__main__":
    create_qr_with_label()
