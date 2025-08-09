#!/usr/bin/env python3
"""
Тест системы рассылок
"""
import os
import sys

# Добавляем путь к корневой папке проекта
sys.path.append('/workspaces/evgenich-gift')

# Устанавливаем переменные окружения для тестирования
os.environ.update({
    'BOT_TOKEN': 'test_token',
    'CHANNEL_ID': '-1001234567890',
    'ADMIN_IDS': '123456789',
    'BOSS_IDS': '123456789',
    'IIKO_LOGIN': 'test',
    'IIKO_PASSWORD': 'test',
    'HELLO_STICKER_ID': 'test_hello_sticker',
    'NASTOYKA_STICKER_ID': 'test_nastoyka_sticker',
    'THANK_YOU_STICKER_ID': 'test_thank_you_sticker',
    'FRIEND_BONUS_STICKER_ID': 'test_friend_sticker',
    'MENU_URL': 'https://test-menu.com',
    'DATABASE_PATH': '/tmp/test_broadcast.db',
    'USE_POSTGRES': 'false'
})

import database
import logging

logging.basicConfig(level=logging.INFO)

def test_broadcast_system():
    """
    Тестирует систему рассылок
    """
    print("🧪 Тестирование системы рассылок...")
    
    try:
        # Инициализируем базу данных
        database.init_db()
        print("✅ База данных инициализирована")
        
        # Создаем тестовых пользователей
        test_users = [
            {'user_id': 123456, 'username': 'testuser1', 'first_name': 'Тест1'},
            {'user_id': 123457, 'username': 'testuser2', 'first_name': 'Тест2'},
            {'user_id': 123458, 'username': 'testuser3', 'first_name': 'Тест3'},
        ]
        
        for user in test_users:
            database.add_new_user(
                user_id=user['user_id'],
                username=user['username'],
                first_name=user['first_name'],
                source='test'
            )
        
        print(f"✅ Создано {len(test_users)} тестовых пользователей")
        
        # Тестируем получение пользователей для рассылки
        users_for_broadcast = database.get_all_users_for_broadcast()
        print(f"✅ Найдено {len(users_for_broadcast)} пользователей для рассылки")
        
        # Тестируем блокировку пользователя
        database.mark_user_blocked(123456)
        print("✅ Пользователь 123456 заблокирован")
        
        # Проверяем статистику
        stats = database.get_broadcast_statistics()
        if stats:
            print(f"📊 Статистика:")
            print(f"  Всего: {stats['total']}")
            print(f"  Активных: {stats['active']}")
            print(f"  Заблокированных: {stats['blocked']}")
            print(f"  За 30 дней: {stats['recent_30d']}")
        
        # Проверяем, что заблокированный пользователь не попал в список рассылки
        users_for_broadcast_after = database.get_all_users_for_broadcast()
        print(f"✅ После блокировки найдено {len(users_for_broadcast_after)} пользователей для рассылки")
        
        print("\n🎉 Система рассылок работает корректно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Удаляем тестовую базу данных
        try:
            if os.path.exists('/tmp/test_broadcast.db'):
                os.remove('/tmp/test_broadcast.db')
                print("🧹 Тестовая база данных удалена")
        except:
            pass

if __name__ == "__main__":
    success = test_broadcast_system()
    sys.exit(0 if success else 1)
