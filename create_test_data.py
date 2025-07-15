#!/usr/bin/env python3
# create_test_data.py

import sys
import os
sys.path.append('/workspaces/evgenich-gift')

import database
import datetime

def create_test_newsletter_data():
    """Создает тестовые данные для всех таблиц рассылок."""
    
    print("🔧 Создание тестовых данных для системы рассылок...")
    
    try:
        conn = database.get_db_connection()
        cur = conn.cursor()
        
        # 1. Создаем тестовую рассылку
        test_newsletter_data = (
            "🎉 Тестовая рассылка",
            "Привет! Это тестовое сообщение нашей новой системы рассылок. Добро пожаловать в мир качественного контента! 🚀",
            12345,  # created_by (замените на реальный admin ID)
            'text',  # media_type
            None,    # media_file_id
            'draft', # status
            datetime.datetime.now()
        )
        
        cur.execute("""
            INSERT INTO newsletters (title, content, created_by, media_type, media_file_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, test_newsletter_data)
        
        newsletter_id = cur.lastrowid
        print(f"✅ Создана тестовая рассылка с ID {newsletter_id}")
        
        # 2. Добавляем тестовые кнопки к рассылке
        test_buttons = [
            (newsletter_id, "🌐 Наш сайт", "https://evgenich.ru?utm_source=telegram&utm_medium=newsletter&utm_campaign=test_button", "telegram", "newsletter", "test_button"),
            (newsletter_id, "📅 Забронировать стол", "https://evgenich.ru/booking?utm_source=telegram&utm_medium=newsletter&utm_campaign=booking_test", "telegram", "newsletter", "booking_test"),
            (newsletter_id, "🍽 Меню", "https://evgenich.ru/menu?utm_source=telegram&utm_medium=newsletter&utm_campaign=menu_test", "telegram", "newsletter", "menu_test")
        ]
        
        for button_data in test_buttons:
            cur.execute("""
                INSERT INTO newsletter_buttons (newsletter_id, text, url, utm_source, utm_medium, utm_campaign)
                VALUES (?, ?, ?, ?, ?, ?)
            """, button_data)
        
        print("✅ Добавлены 3 тестовые кнопки")
        
        # 3. Создаем тестовую статистику доставки (имитируем доставку нескольким пользователям)
        test_stats_data = []
        for i in range(5):  # Создаем 5 записей доставки
            test_stats_data.append((newsletter_id, 999990 + i, datetime.datetime.now()))
        
        for stats_data in test_stats_data:
            cur.execute("""
                INSERT INTO newsletter_stats (newsletter_id, user_id, delivered_at)
                VALUES (?, ?, ?)
            """, stats_data)
        
        print("✅ Добавлена тестовая статистика доставки (5 записей)")
        
        # 4. Создаем тестовые клики по кнопкам
        # Получаем ID кнопок
        cur.execute("SELECT id FROM newsletter_buttons WHERE newsletter_id = ?", (newsletter_id,))
        button_ids = [row[0] for row in cur.fetchall()]
        
        test_clicks_data = []
        for i, button_id in enumerate(button_ids):
            # Создаем разное количество кликов для каждой кнопки
            clicks_count = (i + 1) * 5  # 5, 10, 15 кликов
            for j in range(clicks_count):
                test_clicks_data.append((
                    newsletter_id,
                    button_id,
                    999990 + j,  # Фиктивный user_id
                    datetime.datetime.now()
                ))
        
        for click_data in test_clicks_data:
            cur.execute("""
                INSERT INTO newsletter_clicks (newsletter_id, button_id, user_id, clicked_at)
                VALUES (?, ?, ?, ?)
            """, click_data)
        
        print(f"✅ Добавлено {len(test_clicks_data)} тестовых кликов")
        
        # 5. Создаем еще одну отправленную рассылку для статистики
        sent_newsletter_data = (
            "📢 Отправленная рассылка",
            "Это пример уже отправленной рассылки с реальной статистикой кликов и доставки.",
            12345,  # created_by
            'text',
            None,
            'sent',  # статус отправлена
            datetime.datetime.now() - datetime.timedelta(days=1)  # создана вчера
        )
        
        cur.execute("""
            INSERT INTO newsletters (title, content, created_by, media_type, media_file_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sent_newsletter_data)
        
        sent_newsletter_id = cur.lastrowid
        print(f"✅ Создана отправленная рассылка с ID {sent_newsletter_id}")
        
        # Добавляем статистику доставки для отправленной рассылки
        for i in range(10):  # 10 доставок
            cur.execute("""
                INSERT INTO newsletter_stats (newsletter_id, user_id, delivered_at)
                VALUES (?, ?, ?)
            """, (sent_newsletter_id, 999980 + i, datetime.datetime.now() - datetime.timedelta(days=1)))
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Все тестовые данные успешно созданы!")
        print(f"📧 Создано рассылок: 2")
        print(f"🔘 Создано кнопок: 3")
        print(f"📊 Создано доставок: 15")
        print(f"👆 Создано кликов: {len(test_clicks_data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания тестовых данных: {e}")
        return False

if __name__ == "__main__":
    create_test_newsletter_data()
