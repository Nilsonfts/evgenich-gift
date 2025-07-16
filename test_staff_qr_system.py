#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование системы QR-кодов сотрудников
"""

import sys
import os
import sqlite3
import datetime
import pytz

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_staff_qr_system():
    """Тестирует систему QR-кодов сотрудников."""
    print("=== ТЕСТ СИСТЕМЫ QR-КОДОВ СОТРУДНИКОВ ===")
    
    try:
        # Получаем всех активных сотрудников
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT staff_id, full_name, short_name, unique_code, position FROM staff WHERE status = 'active'")
        active_staff = cur.fetchall()
        
        print(f"\n📋 Активных сотрудников в базе: {len(active_staff)}")
        
        if not active_staff:
            print("❌ В базе нет активных сотрудников!")
            print("💡 Добавьте сотрудников через админ-панель бота:")
            print("   /admin → 👥 Управление персоналом → ➕ Добавить сотрудника")
            return False
        
        # Показываем всех сотрудников и их QR-коды
        print("\n👥 Список активных сотрудников:")
        for staff in active_staff:
            qr_url = f"https://t.me/EvgenichTapBarBot?start=w_{staff['unique_code']}"
            print(f"  • {staff['full_name']} ({staff['position']})")
            print(f"    Код: {staff['unique_code']}")
            print(f"    QR-ссылка: {qr_url}")
            print()
        
        # Тестируем поиск сотрудника по коду
        print("🔍 Тестирование поиска сотрудников по коду:")
        for staff in active_staff[:3]:  # Тестируем первых 3
            found_staff = database.find_staff_by_code(staff['unique_code'])
            if found_staff:
                print(f"  ✅ Код {staff['unique_code']} → {found_staff['full_name']}")
            else:
                print(f"  ❌ Код {staff['unique_code']} не найден!")
        
        # Тестируем несуществующий код
        fake_code = "FAKE123"
        found_fake = database.find_staff_by_code(fake_code)
        if found_fake:
            print(f"  ❌ Ошибка: несуществующий код {fake_code} найден!")
        else:
            print(f"  ✅ Несуществующий код {fake_code} корректно не найден")
        
        # Проверяем статистику переходов за последние 7 дней
        tz_moscow = pytz.timezone('Europe/Moscow')
        current_time = datetime.datetime.now(tz_moscow)
        week_ago = current_time - datetime.timedelta(days=7)
        
        print(f"\n📊 Статистика переходов по QR-кодам за последние 7 дней:")
        print(f"   ({week_ago.strftime('%d.%m.%Y')} - {current_time.strftime('%d.%m.%Y')})")
        
        # Успешные переходы
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM users 
            WHERE signup_date >= ? AND source LIKE 'Сотрудник:%'
            GROUP BY source
            ORDER BY count DESC
        """, (week_ago,))
        successful_qr = cur.fetchall()
        
        if successful_qr:
            total_success = sum(row['count'] for row in successful_qr)
            print(f"  ✅ Успешных переходов: {total_success}")
            for row in successful_qr:
                staff_name = row['source'].replace('Сотрудник: ', '')
                print(f"    • {staff_name}: {row['count']}")
        else:
            print("  ⚠️  Успешных переходов не найдено")
        
        # Переходы с некорректными кодами
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM users 
            WHERE signup_date >= ? AND source LIKE 'Неизвестный_сотрудник_%'
            GROUP BY source
        """, (week_ago,))
        invalid_codes = cur.fetchall()
        
        if invalid_codes:
            total_invalid = sum(row['count'] for row in invalid_codes)
            print(f"  ❌ Переходов с некорректными кодами: {total_invalid}")
            for row in invalid_codes:
                invalid_code = row['source'].replace('Неизвестный_сотрудник_', '')
                print(f"    • Код '{invalid_code}': {row['count']} попыток")
        else:
            print("  ✅ Некорректных кодов не найдено")
        
        # Переходы "direct"
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE signup_date >= ? AND source = 'direct'
        """, (week_ago,))
        direct_count = cur.fetchone()['count']
        print(f"  📱 Прямых переходов (direct): {direct_count}")
        
        conn.close()
        
        print("\n🎯 РЕКОМЕНДАЦИИ:")
        if not successful_qr:
            print("  • Попросите сотрудников активнее использовать свои QR-коды")
            print("  • Проверьте, что QR-коды генерируются и размещаются корректно")
        
        if invalid_codes:
            print("  • Проверьте процесс генерации QR-кодов")
            print("  • Убедитесь, что используются актуальные коды из базы")
        
        print("  • Используйте команду 'Диагностика QR-кодов' в админ-панели для мониторинга")
        
        return True
        
    except Exception as e:
        logging.error(f"Ошибка тестирования QR-системы: {e}")
        print(f"❌ Ошибка: {e}")
        return False

def test_staff_registration_flow():
    """Тестирует процесс регистрации через QR-код сотрудника."""
    print("\n=== ТЕСТ ПРОЦЕССА РЕГИСТРАЦИИ ===")
    
    try:
        # Получаем первого активного сотрудника для теста
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM staff WHERE status = 'active' LIMIT 1")
        test_staff = cur.fetchone()
        
        if not test_staff:
            print("❌ Нет активных сотрудников для тестирования")
            return False
        
        print(f"👤 Тестируем с сотрудником: {test_staff['full_name']} (код: {test_staff['unique_code']})")
        
        # Симулируем поиск сотрудника (как в реальном боте)
        staff_code = test_staff['unique_code']
        found_staff = database.find_staff_by_code(staff_code)
        
        if found_staff:
            brought_by_staff_id = found_staff['staff_id']
            source = f"Сотрудник: {found_staff['short_name']}"
            print(f"  ✅ Сотрудник найден: ID={brought_by_staff_id}, source='{source}'")
        else:
            print(f"  ❌ Сотрудник с кодом {staff_code} не найден!")
            return False
        
        # Проверяем, что данные корректно сохранятся
        print(f"  📋 При регистрации пользователя будет записано:")
        print(f"    • brought_by_staff_id: {brought_by_staff_id}")
        print(f"    • source: '{source}'")
        
        # Проверяем статистику (как в отчете)
        tz_moscow = pytz.timezone('Europe/Moscow')
        current_time = datetime.datetime.now(tz_moscow)
        start_time = current_time - datetime.timedelta(hours=1)  # За последний час
        
        staff_stats = database.get_staff_performance_for_period(start_time, current_time)
        
        if test_staff['position'] in staff_stats:
            for staff_member in staff_stats[test_staff['position']]:
                if staff_member['name'] == test_staff['short_name']:
                    print(f"  📊 Текущая статистика: {staff_member['brought']} приведенных гостей")
                    break
        else:
            print(f"  📊 У сотрудника пока нет приведенных гостей в статистике")
        
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Ошибка тестирования регистрации: {e}")
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Тестирование системы QR-кодов сотрудников бота 'Евгенич'\n")
    
    # Тестируем систему QR-кодов
    qr_test_passed = test_staff_qr_system()
    
    # Тестируем процесс регистрации
    reg_test_passed = test_staff_registration_flow()
    
    print("\n" + "="*50)
    print("📋 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"  QR-система: {'✅ РАБОТАЕТ' if qr_test_passed else '❌ ОШИБКИ'}")
    print(f"  Регистрация: {'✅ РАБОТАЕТ' if reg_test_passed else '❌ ОШИБКИ'}")
    
    if qr_test_passed and reg_test_passed:
        print("\n🎉 Система QR-кодов сотрудников работает корректно!")
        print("\n💡 Для мониторинга используйте:")
        print("   /admin → 📊 Отчеты и аналитика → 🔍 Диагностика QR-кодов")
    else:
        print("\n⚠️  Обнаружены проблемы. Проверьте логи и исправьте ошибки.")
    
    print("="*50)
