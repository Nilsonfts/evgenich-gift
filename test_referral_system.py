#!/usr/bin/env python3
"""
Скрипт для тестирования реферальной системы
"""
import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
import pytz

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = 'dummy'
os.environ['CHANNEL_ID'] = '-100000000'
os.environ['ADMIN_IDS'] = '123456789'
os.environ['BOSS_IDS'] = '123456789'
os.environ['HELLO_STICKER_ID'] = 'dummy'
os.environ['NASTOYKA_STICKER_ID'] = 'dummy' 
os.environ['THANK_YOU_STICKER_ID'] = 'dummy'

# Импортируем database
import database

def create_test_data():
    """Создает тестовые данные для реферальной системы"""
    try:
        print("🧪 Создание тестовых данных для реферальной системы...")
        
        # Инициализируем базу
        database.init_db()
        
        # Создаем тестового реферера (пригласителя)
        referrer_id = 100001
        database.add_new_user(
            user_id=referrer_id,
            username="referrer_user",
            first_name="Алекс",
            source="direct"
        )
        print(f"✅ Создан пользователь-реферер: {referrer_id}")
        
        # Создаем рефералов с разными статусами
        current_time = datetime.now(pytz.utc)
        
        # Реферал 1: Зарегистрировался 3 дня назад, получил настойку 
        ref1_id = 200001
        ref1_signup = current_time - timedelta(days=3)
        database.add_new_user(
            user_id=ref1_id,
            username="friend1",
            first_name="Мария",
            source="referral",
            referrer_id=referrer_id
        )
        # Обновляем дату регистрации и добавляем дату погашения
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET signup_date = ?, redeem_date = ?
            WHERE user_id = ?
        """, (ref1_signup.isoformat(), (current_time - timedelta(days=1)).isoformat(), ref1_id))
        conn.commit()
        conn.close()
        print(f"✅ Реферал 1: {ref1_id} (готов к награде - 72 часа)")
        
        # Реферал 2: Зарегистрировался 1 день назад, получил настойку
        ref2_id = 200002
        ref2_signup = current_time - timedelta(days=1)
        database.add_new_user(
            user_id=ref2_id,
            username="friend2",
            first_name="Иван",
            source="referral",
            referrer_id=referrer_id
        )
        # Обновляем дату регистрации и добавляем дату погашения
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET signup_date = ?, redeem_date = ?
            WHERE user_id = ?
        """, (ref2_signup.isoformat(), current_time.isoformat(), ref2_id))
        conn.commit()
        conn.close()
        print(f"✅ Реферал 2: {ref2_id} (ожидание 24 часа)")
        
        # Реферал 3: Зарегистрировался недавно, НЕ получил настойку
        ref3_id = 200003
        ref3_signup = current_time - timedelta(hours=12)
        database.add_new_user(
            user_id=ref3_id,
            username="friend3",
            first_name="Анна",
            source="referral",
            referrer_id=referrer_id
        )
        # Только обновляем дату регистрации
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET signup_date = ?
            WHERE user_id = ?
        """, (ref3_signup.isoformat(), ref3_id))
        conn.commit()
        conn.close()
        print(f"✅ Реферал 3: {ref3_id} (не получил настойку)")
        
        return referrer_id
        
    except Exception as e:
        print(f"❌ Ошибка создания тестовых данных: {e}")
        return None

def test_referral_functions(referrer_id):
    """Тестирует функции реферальной системы"""
    try:
        print(f"\n🧪 Тестирование функций для реферера {referrer_id}...")
        
        # Тестируем получение статистики
        stats = database.get_referral_stats(referrer_id)
        if stats:
            print(f"📊 Статистика рефералов:")
            print(f"  • Всего: {stats['total']}")
            print(f"  • Получили настойку: {stats['redeemed']}")
            print(f"  • Наград получено: {stats['rewarded']}")
            print(f"  • Ожидают награды: {len(stats['pending'])}")
            
            print("\n🔍 Детали ожидающих:")
            for ref in stats['pending']:
                status = "✅ Готов" if ref['can_claim'] else f"⏰ Осталось {ref['hours_left']}ч"
                print(f"  • {ref['first_name']}: {status}")
        
        # Тестируем проверку прав на награду для первого реферала
        ref1_id = 200001
        eligible, reason = database.check_referral_reward_eligibility(referrer_id, ref1_id)
        print(f"\n🎁 Проверка награды за реферала {ref1_id}:")
        print(f"  Результат: {'✅' if eligible else '❌'} {reason}")
        
        if eligible:
            # Тестируем выдачу награды
            success = database.mark_referral_rewarded(referrer_id, ref1_id)
            print(f"  Выдача награды: {'✅ Успешно' if success else '❌ Ошибка'}")
        
        # Проверяем второго реферала (должен быть не готов)
        ref2_id = 200002
        eligible2, reason2 = database.check_referral_reward_eligibility(referrer_id, ref2_id)
        print(f"\n🎁 Проверка награды за реферала {ref2_id}:")
        print(f"  Результат: {'✅' if eligible2 else '❌'} {reason2}")
        
        # Проверяем третьего реферала (не получил настойку)
        ref3_id = 200003
        eligible3, reason3 = database.check_referral_reward_eligibility(referrer_id, ref3_id)
        print(f"\n🎁 Проверка награды за реферала {ref3_id}:")
        print(f"  Результат: {'✅' if eligible3 else '❌'} {reason3}")
        
        # Проверяем обновленную статистику
        stats_after = database.get_referral_stats(referrer_id)
        if stats_after:
            print(f"\n📊 Обновленная статистика:")
            print(f"  • Наград получено: {stats_after['rewarded']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    # Создаем тестовые данные
    referrer_id = create_test_data()
    
    if referrer_id:
        # Тестируем функции
        success = test_referral_functions(referrer_id)
        
        if success:
            print("\n🎉 Все тесты прошли успешно!")
            print("\n💡 Теперь можно тестировать в боте:")
            print(f"   1. Отправьте /friend или нажмите 'Привести товарища'")
            print(f"   2. Проверьте статистику и кнопку получения наград")
        else:
            print("\n❌ Некоторые тесты не прошли")
    else:
        print("\n❌ Не удалось создать тестовые данные")
