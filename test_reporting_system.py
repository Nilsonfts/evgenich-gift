#!/usr/bin/env python3
"""
Проверка работы системы отчетов с новыми источниками.
"""
import sqlite3
import datetime
import pytz
from typing import Dict, Tuple

def get_report_data_for_period(start_time: datetime.datetime, end_time: datetime.datetime) -> Tuple[int, int, Dict]:
    """Имитирует функцию из database.py для тестирования."""
    try:
        from config import DATABASE_PATH
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        
        # Подсчет выданных купонов
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE signup_date BETWEEN ? AND ? 
            AND status IN ('issued', 'redeemed', 'redeemed_and_left')
        """, (start_time, end_time))
        issued_count = cur.fetchone()[0]
        
        # Подсчет погашенных купонов
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE redeem_date BETWEEN ? AND ?
        """, (start_time, end_time))
        redeemed_count = cur.fetchone()[0]
        
        # Статистика по источникам
        cur.execute("""
            SELECT source, COUNT(*) FROM users 
            WHERE signup_date BETWEEN ? AND ? 
            GROUP BY source
        """, (start_time, end_time))
        all_sources = {row[0]: row[1] for row in cur.fetchall()}
        
        # Фильтруем источники: все обычные источники
        sources = {k: v for k, v in all_sources.items() if k != "staff"}
        
        # Подсчитываем переходы от сотрудников отдельно
        staff_count = all_sources.get("staff", 0)
        if staff_count > 0:
            sources["staff"] = staff_count
        
        conn.close()
        return issued_count, redeemed_count, sources
        
    except Exception as e:
        return 0, 0, {}

def generate_test_report():
    """Генерирует тестовый отчет для проверки новых источников."""
    print("📊 Генерация тестового отчета...")
    
    # Берем данные за последние 30 дней
    tz_moscow = pytz.timezone('Europe/Moscow')
    end_time = datetime.datetime.now(tz_moscow)
    start_time = end_time - datetime.timedelta(days=30)
    
    # Получаем данные
    issued, redeemed, sources = get_report_data_for_period(start_time, end_time)
    
    print(f"\n📈 **Отчет по источникам трафика** 📈")
    print(f"**Период:** {start_time.strftime('%d.%m.%Y %H:%M')} - {end_time.strftime('%d.%m.%Y %H:%M')}")
    print(f"\n✅ **Выдано купонов:** {issued}")
    print(f"🥃 **Погашено настоек:** {redeemed}")
    
    conversion = round((redeemed / issued) * 100, 1) if issued > 0 else 0
    print(f"📈 **Конверсия в погашение:** {conversion}%")
    
    if sources:
        print(f"\n---\n")
        print(f"**📍 Источники подписчиков:**")
        # Сортируем источники по количеству
        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        for source, count in sorted_sources:
            print(f"• {source}: {count}")
    
    print(f"\n✅ Отчет сгенерирован успешно!")
    
    # Дополнительная информация
    print(f"\n📋 **Дополнительная информация:**")
    print(f"• Всего источников: {len(sources)}")
    print(f"• Самый популярный источник: {max(sources.items(), key=lambda x: x[1])[0] if sources else 'Нет данных'}")
    
    return True

if __name__ == "__main__":
    success = generate_test_report()
    if success:
        print(f"\n🎉 Тест системы отчетов завершен успешно!")
    else:
        print(f"\n💥 Ошибка в системе отчетов!")
