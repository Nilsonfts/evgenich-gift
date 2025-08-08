#!/usr/bin/env python3
"""
Тестирование исправленной системы отчетов
"""

import sqlite3
from datetime import datetime
import logging

# Путь к базе данных
DB_PATH = "data/evgenich_data.db"

def get_report_data_for_period_fixed(start_time: datetime, end_time: datetime) -> tuple:
    """Тестовая версия функции отчетов с исправленным форматом дат"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Конвертируем datetime в строку ISO формата для SQLite
        start_str = start_time.isoformat()
        end_str = end_time.isoformat()
        
        cur.execute("SELECT COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? AND status IN ('issued', 'redeemed', 'redeemed_and_left')", (start_str, end_str))
        issued_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ?", (start_str, end_str))
        redeemed_count = cur.fetchone()[0]
        cur.execute("SELECT source, COUNT(*) FROM users WHERE signup_date BETWEEN ? AND ? GROUP BY source", (start_str, end_str))
        all_sources = {row['source']: row['COUNT(*)'] for row in cur.fetchall()}
        
        # Фильтруем источники: все обычные источники
        sources = {k: v for k, v in all_sources.items() if k != "staff"}
        
        # Подсчитываем переходы от сотрудников отдельно
        staff_count = all_sources.get("staff", 0)
        if staff_count > 0:
            sources["staff"] = staff_count
        total_redeem_time_seconds = 0
        if redeemed_count > 0:
            cur.execute("SELECT SUM(strftime('%s', redeem_date) - strftime('%s', signup_date)) FROM users WHERE redeem_date BETWEEN ? AND ? AND status IN ('redeemed', 'redeemed_and_left')", (start_str, end_str))
            total_redeem_time_seconds_row = cur.fetchone()[0]
            total_redeem_time_seconds = total_redeem_time_seconds_row or 0
        conn.close()
        return issued_count, redeemed_count, [], sources, total_redeem_time_seconds
    except Exception as e:
        logging.error(f"Ошибка сбора данных для отчета в SQLite: {e}")
        return 0, 0, [], {}, 0

def get_daily_churn_data_fixed(start_time: datetime, end_time: datetime) -> tuple:
    """Тестовая версия функции оттока с исправленным форматом дат"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Конвертируем datetime в строку ISO формата для SQLite
        start_str = start_time.isoformat()
        end_str = end_time.isoformat()
        
        cur.execute("SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ? AND status IN ('redeemed', 'redeemed_and_left')", (start_str, end_str))
        redeemed_total = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE redeem_date BETWEEN ? AND ? AND status = 'redeemed_and_left'",
            (start_str, end_str)
        )
        left_count = cur.fetchone()[0]
        conn.close()
        return redeemed_total, left_count
    except Exception as e:
        logging.error(f"Ошибка получения данных о дневном оттоке: {e}")
        return 0, 0

def test_report_system():
    """Тестирует всю систему отчетов"""
    print("🔍 Тестирование исправленной системы отчетов")
    
    # Период из сообщения пользователя
    start_time = datetime(2025, 8, 8, 12, 0)
    end_time = datetime(2025, 8, 8, 16, 44)
    
    print(f"📅 Период: {start_time.strftime('%d.%m %H:%M')} - {end_time.strftime('%d.%m %H:%M')}")
    print()
    
    # Тестируем основные функции
    general_stats = get_report_data_for_period_fixed(start_time, end_time)
    issued, redeemed, _, sources, total_redeem_time = general_stats
    
    print("📊 Основная статистика:")
    print(f"  🎫 Выдано подарков: {issued}")
    print(f"  🎁 Активировано подарков: {redeemed}")
    print(f"  ⏱️  Общее время активации: {total_redeem_time} сек.")
    
    if issued > 0:
        conversion_rate = round((redeemed / issued) * 100, 1)
        print(f"  📈 Конверсия: {conversion_rate}%")
    
    print()
    
    # Источники
    if sources:
        print("📊 Источники трафика:")
        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        for source, count in sorted_sources:
            print(f"  • {source}: {count}")
    else:
        print("📊 Нет данных по источникам")
    
    print()
    
    # Отток
    redeemed_total, left_count = get_daily_churn_data_fixed(start_time, end_time)
    print("📉 Анализ оттока:")
    print(f"  👥 Всего активировало: {redeemed_total}")
    print(f"  👋 Покинули заведение: {left_count}")
    
    if redeemed_total > 0:
        retention_rate = round(((redeemed_total - left_count) / redeemed_total) * 100, 1)
        print(f"  🎯 Удержание: {retention_rate}%")
    
    print()
    
    # Проверим, что теперь функция не вернет "нет данных"
    if issued == 0:
        print("❌ Проблема НЕ решена: все еще нет данных")
        print("За период с 08.08 12:00 по 08.08 16:44 нет данных для отчета по текущей смены.")
    else:
        print("✅ Проблема РЕШЕНА: данные найдены!")
        print(f"За период с 08.08 12:00 по 08.08 16:44 найдено {issued} выданных подарков")

if __name__ == "__main__":
    test_report_system()
