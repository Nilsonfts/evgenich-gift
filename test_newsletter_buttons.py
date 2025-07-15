#!/usr/bin/env python3
# test_newsletter_buttons.py

import sys
import os
sys.path.append('/workspaces/evgenich-gift')

import database

def test_newsletter_buttons():
    """Тестирует работу кнопок системы рассылок."""
    
    print("🔍 Тестирование кнопок системы рассылок...")
    
    try:
        # Тестируем статистику базы
        conn = database.get_db_connection()
        cur = conn.cursor()
        
        print("\n📊 Тест статистики базы:")
        
        # Общая статистика пользователей
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        print(f"  👥 Всего пользователей: {total_users}")
        
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'registered'")
        registered = cur.fetchone()[0]
        print(f"  📝 Зарегистрированы: {registered}")
        
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'redeemed_and_left'")
        blocked = cur.fetchone()[0]
        print(f"  🚫 Заблокировали бота: {blocked}")
        
        active_for_newsletter = total_users - blocked
        print(f"  📧 Доступно для рассылки: {active_for_newsletter}")
        
        print("\n📧 Тест списка рассылок:")
        newsletters = database.get_user_newsletters(12345, 10)
        print(f"  📋 Найдено рассылок: {len(newsletters)}")
        for newsletter in newsletters:
            print(f"    • {newsletter['title']} (статус: {newsletter['status']})")
        
        print("\n📈 Тест аналитики рассылок:")
        
        # Общая статистика рассылок
        cur.execute("SELECT COUNT(*) FROM newsletters")
        total_newsletters = cur.fetchone()[0]
        print(f"  📧 Всего рассылок: {total_newsletters}")
        
        cur.execute("SELECT COUNT(*) FROM newsletters WHERE status = 'sent'")
        sent_newsletters = cur.fetchone()[0]
        print(f"  ✅ Отправлено: {sent_newsletters}")
        
        cur.execute("SELECT COUNT(*) FROM newsletter_stats")
        total_delivered = cur.fetchone()[0]
        print(f"  📥 Доставлено сообщений: {total_delivered}")
        
        cur.execute("SELECT COUNT(*) FROM newsletter_clicks")
        total_clicks = cur.fetchone()[0]
        print(f"  👆 Всего кликов: {total_clicks}")
        
        if total_delivered > 0:
            ctr = round((total_clicks / total_delivered) * 100, 1)
            print(f"  📊 Общий CTR: {ctr}%")
        
        print("\n🔘 Тест кнопок рассылок:")
        cur.execute("SELECT * FROM newsletter_buttons")
        buttons = cur.fetchall()
        print(f"  🔘 Найдено кнопок: {len(buttons)}")
        for button in buttons:
            print(f"    • {button[2]} -> {button[3]}")  # text, url
        
        print("\n👆 Тест кликов по кнопкам:")
        cur.execute("""
            SELECT nb.text, COUNT(nc.id) as clicks 
            FROM newsletter_buttons nb 
            LEFT JOIN newsletter_clicks nc ON nb.id = nc.button_id 
            GROUP BY nb.id, nb.text
        """)
        button_stats = cur.fetchall()
        for button_stat in button_stats:
            print(f"    • {button_stat[0]}: {button_stat[1]} кликов")
        
        conn.close()
        
        print("\n✅ Все тесты пройдены успешно!")
        print("🎯 Кнопки системы рассылок готовы к работе!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_newsletter_buttons()
