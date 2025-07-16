#!/usr/bin/env python3
"""
Создание QR-кодов с подписями имени и фамилии сотрудников
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

def create_qr_with_name(staff_member, output_dir="qr_codes_with_names"):
    """Создает QR-код с подписью имени и фамилии."""
    
    # Создаем директорию, если её нет
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Данные
    full_name = staff_member['full_name']
    position = staff_member['position']
    telegram_id = staff_member['telegram_id']
    unique_code = staff_member['unique_code']
    
    # Правильная ссылка
    url = f"https://t.me/evgenichspbbot?start=w_{unique_code}"
    
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Создаем изображение QR-кода
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Размеры
    qr_size = qr_img.size
    text_height = 80  # Высота для текста
    total_width = qr_size[0]
    total_height = qr_size[1] + text_height
    
    # Создаем финальное изображение с белым фоном
    final_img = Image.new('RGB', (total_width, total_height), 'white')
    
    # Вставляем QR-код
    final_img.paste(qr_img, (0, 0))
    
    # Добавляем текст
    draw = ImageDraw.Draw(final_img)
    
    try:
        # Пытаемся использовать системный шрифт
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        # Если системный шрифт не найден, используем стандартный
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Текст для подписи
    name_text = full_name
    position_text = f"({position})"
    id_text = f"ID: {telegram_id}"
    
    # Позиции для центрирования текста
    text_y_start = qr_size[1] + 5
    
    # Имя и фамилия (крупно)
    try:
        name_bbox = draw.textbbox((0, 0), name_text, font=font_large)
        name_width = name_bbox[2] - name_bbox[0]
    except:
        name_width = len(name_text) * 12  # Приблизительная ширина
    name_x = (total_width - name_width) // 2
    draw.text((name_x, text_y_start), name_text, fill="black", font=font_large)
    
    # Должность (мельче)
    try:
        pos_bbox = draw.textbbox((0, 0), position_text, font=font_small)
        pos_width = pos_bbox[2] - pos_bbox[0]
    except:
        pos_width = len(position_text) * 10  # Приблизительная ширина
    pos_x = (total_width - pos_width) // 2
    draw.text((pos_x, text_y_start + 25), position_text, fill="gray", font=font_small)
    
    # ID (совсем мелко)
    try:
        id_bbox = draw.textbbox((0, 0), id_text, font=font_small)
        id_width = id_bbox[2] - id_bbox[0]
    except:
        id_width = len(id_text) * 10  # Приблизительная ширина
    id_x = (total_width - id_width) // 2
    draw.text((id_x, text_y_start + 45), id_text, fill="gray", font=font_small)
    
    # Сохраняем файл
    filename = f"{output_dir}/{full_name.replace(' ', '_')}_{unique_code}.png"
    final_img.save(filename)
    
    return filename, url

def main():
    """Создаем QR-коды с подписями для всех сотрудников."""
    print("🎯 СОЗДАНИЕ QR-КОДОВ С ПОДПИСЯМИ ИМЕН")
    print("=" * 50)
    
    # Получаем сотрудников из базы
    staff_list = get_staff_from_db()
    
    if not staff_list:
        print("❌ Нет активных сотрудников в базе данных")
        return
    
    print(f"👥 Найдено {len(staff_list)} активных сотрудников")
    print()
    
    for staff in staff_list:
        print(f"📝 Создаю QR-код для: {staff['full_name']}")
        
        try:
            filename, url = create_qr_with_name(staff)
            print(f"✅ Создан: {filename}")
            print(f"🔗 Ссылка: {url}")
            print(f"👤 Подпись: {staff['full_name']} ({staff['position']})")
            print()
            
        except Exception as e:
            print(f"❌ Ошибка для {staff['full_name']}: {e}")
            print()
    
    print("🎉 Все QR-коды с подписями созданы!")
    print("📁 Файлы сохранены в папке 'qr_codes_with_names/'")
    print("🖨️ Готовы к печати!")

if __name__ == "__main__":
    main()
