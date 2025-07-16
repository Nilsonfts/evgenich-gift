#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая диагностика системы QR-кодов сотрудников
"""

import sqlite3
import datetime
import pytz

def test_database_structure():
    """Проверяет структуру базы данных."""
    print("=== ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ ===")
    
    try:
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Проверяем таблицу staff
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staff'")
        if cur.fetchone():
            print("✅ Таблица 'staff' существует")
            
            # Проверяем структуру
            cur.execute("PRAGMA table_info(staff)")
            staff_columns = [row[1] for row in cur.fetchall()]
            required_columns = ['staff_id', 'full_name', 'short_name', 'unique_code', 'position', 'status']
            
            for col in required_columns:
                if col in staff_columns:
                    print(f"  ✅ Колонка '{col}' есть")
                else:
                    print(f"  ❌ Колонка '{col}' отсутствует")
        else:
            print("❌ Таблица 'staff' не существует")
            return False
        
        # Проверяем таблицу users
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cur.fetchone():
            print("✅ Таблица 'users' существует")
            
            cur.execute("PRAGMA table_info(users)")
            user_columns = [row[1] for row in cur.fetchall()]
            required_columns = ['user_id', 'source', 'brought_by_staff_id']
            
            for col in required_columns:
                if col in user_columns:
                    print(f"  ✅ Колонка '{col}' есть")
                else:
                    print(f"  ❌ Колонка '{col}' отсутствует")
        else:
            print("❌ Таблица 'users' не существует")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки структуры: {e}")
        return False

def test_staff_data():
    """Проверяет данные сотрудников."""
    print("\n=== ПРОВЕРКА ДАННЫХ СОТРУДНИКОВ ===")
    
    try:
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Получаем всех сотрудников
        cur.execute("SELECT COUNT(*) as total FROM staff")
        total_staff = cur.fetchone()['total']
        print(f"📊 Всего сотрудников в базе: {total_staff}")
        
        # Получаем активных сотрудников
        cur.execute("SELECT COUNT(*) as active FROM staff WHERE status = 'active'")
        active_staff = cur.fetchone()['active']
        print(f"👥 Активных сотрудников: {active_staff}")
        
        if active_staff == 0:
            print("⚠️  Нет активных сотрудников!")
            print("💡 Добавьте сотрудников через админ-панель бота:")
            print("   /admin → 👥 Управление персоналом → ➕ Добавить сотрудника")
            return False
        
        # Показываем активных сотрудников
        cur.execute("SELECT * FROM staff WHERE status = 'active'")
        staff_list = cur.fetchall()
        
        print(f"\n👥 Список активных сотрудников:")
        for staff in staff_list:
            qr_url = f"https://t.me/EvgenichTapBarBot?start=w_{staff['unique_code']}"
            print(f"  • {staff['full_name']} ({staff['position']})")
            print(f"    Код: {staff['unique_code']}")
            print(f"    QR-ссылка: {qr_url}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки данных сотрудников: {e}")
        return False

def test_qr_statistics():
    """Проверяет статистику переходов по QR-кодам."""
    print("\n=== СТАТИСТИКА QR-КОДОВ ===")
    
    try:
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Статистика за последние 7 дней
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        # Успешные переходы по QR-кодам сотрудников
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
            print(f"✅ Успешных переходов по QR-кодам за 7 дней: {total_success}")
            for row in successful_qr:
                staff_name = row['source'].replace('Сотрудник: ', '')
                print(f"  • {staff_name}: {row['count']}")
        else:
            print("⚠️  Успешных переходов по QR-кодам не найдено")
        
        # Переходы с некорректными кодами
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM users 
            WHERE signup_date >= ? AND source LIKE 'Неизвестный_сотрудник_%'
            GROUP BY source
            ORDER BY count DESC
        """, (week_ago,))
        invalid_codes = cur.fetchall()
        
        if invalid_codes:
            total_invalid = sum(row['count'] for row in invalid_codes)
            print(f"❌ Переходов с некорректными кодами: {total_invalid}")
            for row in invalid_codes:
                invalid_code = row['source'].replace('Неизвестный_сотрудник_', '')
                print(f"  • Некорректный код '{invalid_code}': {row['count']} попыток")
        else:
            print("✅ Некорректных кодов не обнаружено")
        
        # Прямые переходы
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE signup_date >= ? AND source = 'direct'
        """, (week_ago,))
        direct_count = cur.fetchone()['count']
        print(f"📱 Прямых переходов: {direct_count}")
        
        # Все источники
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM users 
            WHERE signup_date >= ?
            GROUP BY source
            ORDER BY count DESC
        """, (week_ago,))
        all_sources = cur.fetchall()
        
        if all_sources:
            print(f"\n📊 Все источники за 7 дней:")
            for row in all_sources:
                print(f"  • {row['source']}: {row['count']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки статистики: {e}")
        return False

def main():
    """Основная функция диагностики."""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ QR-КОДОВ СОТРУДНИКОВ")
    print("=" * 50)
    
    # Проверяем структуру базы данных
    structure_ok = test_database_structure()
    
    if not structure_ok:
        print("\n❌ Проблемы со структурой базы данных!")
        return
    
    # Проверяем данные сотрудников
    staff_ok = test_staff_data()
    
    # Проверяем статистику
    stats_ok = test_qr_statistics()
    
    print("\n" + "=" * 50)
    print("📋 ИТОГИ ДИАГНОСТИКИ:")
    print(f"  Структура БД: {'✅ OK' if structure_ok else '❌ ОШИБКА'}")
    print(f"  Данные сотрудников: {'✅ OK' if staff_ok else '❌ ОШИБКА'}")
    print(f"  Статистика: {'✅ OK' if stats_ok else '❌ ОШИБКА'}")
    
    if structure_ok and staff_ok and stats_ok:
        print("\n🎉 Система готова к работе!")
        print("\n💡 Для тестирования:")
        print("  1. Попросите сотрудника сгенерировать QR-код")
        print("  2. Попросите гостя перейти по ссылке")
        print("  3. Проверьте статистику в админ-панели")
    else:
        print("\n⚠️  Требуется устранение проблем")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
