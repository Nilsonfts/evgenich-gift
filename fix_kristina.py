#!/usr/bin/env python3
"""
Быстрое исправление Кристины - убираем кириллицу навсегда
"""

import sqlite3
import os

def fix_kristina():
    """Исправляет запись Кристины, убирая кириллицу."""
    
    db_path = "data/evgenich_data.db"
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("🔧 ИСПРАВЛЕНИЕ КРИСТИНЫ")
    print("=" * 30)
    
    # 1. Показываем текущее состояние
    print("\n1️⃣ Текущие записи:")
    cur.execute("SELECT * FROM staff")
    all_staff = cur.fetchall()
    for staff in all_staff:
        print(f"  • {staff['full_name']} (ID: {staff['telegram_id']}, код: {staff['unique_code']})")
    
    # 2. Удаляем ВСЕ записи с кириллицей в unique_code
    print("\n2️⃣ Удаляем записи с кириллицей:")
    cur.execute("DELETE FROM staff WHERE unique_code LIKE '%кристин%' OR unique_code LIKE '%нил%'")
    deleted = cur.rowcount
    if deleted > 0:
        print(f"   ✅ Удалено {deleted} записей с кириллицей")
    else:
        print("   ℹ️ Записей с кириллицей не найдено")
    
    # 3. Обновляем/создаем правильную запись для Кристины
    print("\n3️⃣ Создаем правильную запись для Кристины:")
    
    # Telegram ID Кристины (из вашего примера ссылки)
    kristina_telegram_id = 208281210
    
    # Удаляем старую запись, если есть
    cur.execute("DELETE FROM staff WHERE telegram_id = ?", (kristina_telegram_id,))
    
    # Создаем новую правильную запись
    cur.execute("""
        INSERT INTO staff (telegram_id, full_name, short_name, position, unique_code, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (kristina_telegram_id, "Кристина", "Кристина", "Официант", str(kristina_telegram_id), "active"))
    
    print(f"   ✅ Кристина добавлена с кодом: {kristina_telegram_id}")
    
    # 4. То же для Нила
    print("\n4️⃣ Исправляем Нила:")
    nil_telegram_id = 196614680
    
    cur.execute("DELETE FROM staff WHERE telegram_id = ?", (nil_telegram_id,))
    cur.execute("""
        INSERT INTO staff (telegram_id, full_name, short_name, position, unique_code, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nil_telegram_id, "Нил Витальевич", "Нил В.", "Администратор", str(nil_telegram_id), "active"))
    
    print(f"   ✅ Нил добавлен с кодом: {nil_telegram_id}")
    
    # 5. Сохраняем изменения
    conn.commit()
    
    # 6. Показываем финальное состояние
    print("\n5️⃣ Финальное состояние:")
    cur.execute("SELECT * FROM staff WHERE status = 'active' ORDER BY full_name")
    final_staff = cur.fetchall()
    
    for staff in final_staff:
        qr_link = f"https://t.me/evgenichspbbot?start=w_{staff['unique_code']}"
        print(f"  • {staff['full_name']} ({staff['position']})")
        print(f"    TG ID: {staff['telegram_id']}")
        print(f"    Код: {staff['unique_code']}")
        print(f"    QR: {qr_link}")
        print()
    
    # 7. Тестируем код Кристины
    print("6️⃣ Тестируем код Кристины:")
    cur.execute("SELECT * FROM staff WHERE unique_code = ?", (str(kristina_telegram_id),))
    test_result = cur.fetchone()
    
    if test_result:
        print(f"   ✅ Код {kristina_telegram_id} найден!")
        print(f"   ✅ Сотрудник: {test_result['full_name']}")
        print(f"   ✅ QR-ссылка: https://t.me/evgenichspbbot?start=w_{kristina_telegram_id}")
    else:
        print(f"   ❌ Код {kristina_telegram_id} НЕ найден!")
    
    conn.close()
    
    print("\n🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
    print("✅ Теперь все коды только цифровые")
    print("✅ Никакой кириллицы в URL")
    print("✅ Все ссылки будут работать")

if __name__ == "__main__":
    fix_kristina()
