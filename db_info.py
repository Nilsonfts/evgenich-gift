#!/usr/bin/env python3
"""Информация о текущей конфигурации БД."""
import os

print("📊 ИНФОРМАЦИЯ О КОНФИГУРАЦИИ БД")
print("=" * 60)

# Проверяем переменные окружения
use_postgres = os.getenv("USE_POSTGRES", "false").lower() in ("true", "1", "yes")
database_path = os.getenv("DATABASE_PATH", "bot.db")
database_url = os.getenv("DATABASE_URL", "не установлен")

print(f"\n🔧 Текущая конфигурация:")
print(f"   USE_POSTGRES: {use_postgres}")
print(f"   DATABASE_PATH (SQLite): {database_path}")
if use_postgres:
    print(f"   DATABASE_URL (PostgreSQL): ✅ установлен")
else:
    print(f"   DATABASE_URL (PostgreSQL): ❌ не используется")

print(f"\n💾 Среда выполнения:")
if os.path.exists(database_path):
    size = os.path.getsize(database_path)
    print(f"   SQLite БД существует: ✅ ({size} байт)")
else:
    print(f"   SQLite БД существует: ❌ (локально нет данных)")

print(f"\n📌 Где находятся реальные данные:")
print(f"   На Railway (в продакшене): PostgreSQL")
print(f"   Локально (при разработке): SQLite ({database_path})")
print(f"   На GitHub: Никаких боевых данных")

print(f"\n🚀 Для просмотра статистики реальных пользователей:")
print(f"   1. Подключитесь к Railway PostgreSQL")
print(f"   2. Используйте команду: railway connect")
print(f"   3. SELECT COUNT(*) FROM users;")
print(f"   4. SELECT status, COUNT(*) FROM users GROUP BY status;")

print(f"\n📍 Google Sheets ID (где сохраняются данные):")
google_sheet = os.getenv("GOOGLE_SHEET_KEY", "не установлен")
if google_sheet.startswith("1bp7"):
    print(f"   ✅ Установлен")
else:
    print(f"   ❌ Не установлен")

print("\n" + "=" * 60)
