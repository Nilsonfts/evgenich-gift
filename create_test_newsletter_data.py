#!/usr/bin/env python3
# create_test_newsletter_data.py
"""
Создает тестовые данные для системы рассылок.
"""
import sys
import os
sys.path.append('/workspaces/evgenich-gift')

import database
import datetime

def create_test_data():
    """Создает тестовые данные для всех таблиц рассылок."""
    try:
        print("🔧 Создание тестовых данных для системы рассылок...")
        
        conn = database.get_db_connection()
        cur = conn.cursor()
        
        # Создаем тестовые рассылки
        print("📧 Создаем тестовые рассылки...")
        
        newsletters_data = [
            {
                'title': '🎉 Добро пожаловать в Евгенич!',
                'content': 'Привет! Добро пожаловать в наш уютный ресторан. Мы рады видеть тебя среди наших гостей!',
                'media_type': None,
                'status': 'sent',
                'target_count': 150,
                'delivered_count': 142
            },
            {
                'title': '🍽 Новое меню уже здесь!',
                'content': 'Попробуйте наши новые блюда! Шеф-повар приготовил для вас настоящие кулинарные шедевры.',
                'media_type': 'photo',
                'media_file_id': 'test_photo_123',
                'status': 'sent',
                'target_count': 180,
                'delivered_count': 175
            },
            {
                'title': '🎵 Живая музыка в выходные',
                'content': 'В эти выходные у нас выступает группа "Вечерний джаз". Бронируйте столики заранее!',
                'media_type': 'video',
                'media_file_id': 'test_video_456',
                'status': 'sent',
                'target_count': 95,
                'delivered_count': 89
            },
            {
                'title': '📋 Черновик акции',
                'content': 'Скоро у нас будет большая акция...',
                'media_type': None,
                'status': 'draft'
            }
        ]
        
        newsletter_ids = []
        for newsletter in newsletters_data:
            cur.execute("""
                INSERT INTO newsletters (title, content, media_type, media_file_id, status, created_by, 
                                       target_count, delivered_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                newsletter['title'],
                newsletter['content'], 
                newsletter.get('media_type'),
                newsletter.get('media_file_id'),
                newsletter['status'],
                123456789,  # Тестовый admin ID
                newsletter.get('target_count'),
                newsletter.get('delivered_count'),
                datetime.datetime.now()
            ))
            newsletter_ids.append(cur.lastrowid)
        
        print(f"✅ Создано {len(newsletter_ids)} тестовых рассылок")
        
        # Создаем тестовые кнопки
        print("🔘 Создаем тестовые кнопки...")
        
        buttons_data = [
            # Кнопки для первой рассылки
            {
                'newsletter_id': newsletter_ids[0],
                'text': '🌐 Наш сайт',
                'url': 'https://evgenich.ru?utm_source=telegram&utm_medium=newsletter&utm_campaign=welcome',
                'utm_source': 'telegram',
                'utm_medium': 'newsletter', 
                'utm_campaign': 'welcome'
            },
            {
                'newsletter_id': newsletter_ids[0],
                'text': '📞 Связаться',
                'url': 'https://evgenich.ru/contact?utm_source=telegram&utm_medium=newsletter&utm_campaign=welcome',
                'utm_source': 'telegram',
                'utm_medium': 'newsletter',
                'utm_campaign': 'welcome'
            },
            # Кнопки для второй рассылки
            {
                'newsletter_id': newsletter_ids[1],
                'text': '🍽 Посмотреть меню',
                'url': 'https://evgenich.ru/menu?utm_source=telegram&utm_medium=newsletter&utm_campaign=new_menu',
                'utm_source': 'telegram',
                'utm_medium': 'newsletter',
                'utm_campaign': 'new_menu'
            },
            {
                'newsletter_id': newsletter_ids[1], 
                'text': '📅 Забронировать стол',
                'url': 'https://evgenich.ru/booking?utm_source=telegram&utm_medium=newsletter&utm_campaign=new_menu',
                'utm_source': 'telegram',
                'utm_medium': 'newsletter',
                'utm_campaign': 'new_menu'
            },
            # Кнопка для третьей рассылки
            {
                'newsletter_id': newsletter_ids[2],
                'text': '🎵 Забронировать на концерт',
                'url': 'https://evgenich.ru/booking?utm_source=telegram&utm_medium=newsletter&utm_campaign=live_music',
                'utm_source': 'telegram', 
                'utm_medium': 'newsletter',
                'utm_campaign': 'live_music'
            }
        ]
        
        button_ids = []
        for button in buttons_data:
            cur.execute("""
                INSERT INTO newsletter_buttons (newsletter_id, text, url, utm_source, utm_medium, utm_campaign)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                button['newsletter_id'],
                button['text'],
                button['url'],
                button['utm_source'],
                button['utm_medium'],
                button['utm_campaign']
            ))
            button_ids.append(cur.lastrowid)
        
        print(f"✅ Создано {len(button_ids)} тестовых кнопок")
        
        # Создаем тестовую статистику доставки
        print("📊 Создаем тестовую статистику доставки...")
        
        stats_count = 0
        for i, newsletter_id in enumerate(newsletter_ids[:3]):  # Только для отправленных рассылок
            delivered_count = newsletters_data[i]['delivered_count']
            for user_num in range(1, delivered_count + 1):
                test_user_id = 1000000 + user_num  # Тестовые ID пользователей
                cur.execute("""
                    INSERT INTO newsletter_stats (newsletter_id, user_id, delivered_at)
                    VALUES (?, ?, ?)
                """, (newsletter_id, test_user_id, datetime.datetime.now()))
                stats_count += 1
        
        print(f"✅ Создано {stats_count} записей статистики доставки")
        
        # Создаем тестовые клики по кнопкам
        print("🖱 Создаем тестовые клики...")
        
        clicks_data = [
            # Клики по кнопкам первой рассылки
            {'button_id': button_ids[0], 'clicks': 25},  # Наш сайт
            {'button_id': button_ids[1], 'clicks': 12},  # Связаться
            # Клики по кнопкам второй рассылки
            {'button_id': button_ids[2], 'clicks': 45},  # Меню
            {'button_id': button_ids[3], 'clicks': 38},  # Бронирование
            # Клики по кнопке третьей рассылки
            {'button_id': button_ids[4], 'clicks': 18},  # Концерт
        ]
        
        total_clicks = 0
        for click_data in clicks_data:
            for click_num in range(click_data['clicks']):
                test_user_id = 1000000 + click_num + 1
                cur.execute("""
                    INSERT INTO newsletter_clicks (button_id, user_id, clicked_at)
                    VALUES (?, ?, ?)
                """, (click_data['button_id'], test_user_id, datetime.datetime.now()))
                total_clicks += 1
        
        print(f"✅ Создано {total_clicks} тестовых кликов")
        
        # Создаем тестовую отложенную задачу (для примера)
        print("⏰ Создаем тестовую отложенную задачу...")
        
        cur.execute("""
            INSERT INTO delayed_tasks (user_id, task_type, scheduled_time)
            VALUES (?, ?, ?)
        """, (
            1234567890,  # Тестовый user ID
            'send_newsletter',
            datetime.datetime.now() + datetime.timedelta(hours=1)  # Через час
        ))
        
        print("✅ Создана тестовая отложенная задача")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Все тестовые данные успешно созданы!")
        print(f"📧 Рассылок: {len(newsletter_ids)}")
        print(f"🔘 Кнопок: {len(button_ids)}")
        print(f"📊 Записей доставки: {stats_count}")
        print(f"🖱 Кликов: {total_clicks}")
        print("⏰ Отложенных задач: 1")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания тестовых данных: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Инициализируем БД
    print("🔧 Инициализация базы данных...")
    database.init_db()
    
    # Создаем тестовые данные
    create_test_data()
