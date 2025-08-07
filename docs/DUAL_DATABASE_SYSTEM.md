# Система двойной миграции и работы с базами данных

В этом документе описывается система двойной миграции и работы с базами данных PostgreSQL и SQLite, реализованная для бота Evgenich.

## Обзор системы

Система позволяет одновременно работать с двумя базами данных:
- PostgreSQL - основная база данных, хранящаяся на сервере Railway
- SQLite - локальная база данных, используемая для быстрого доступа и как резервная копия

## Возможности системы

1. **Миграция данных из Google Sheets** - Система позволяет мигрировать данные из Google Sheets одновременно в обе базы данных.
2. **Синхронизация данных** - При добавлении новых пользователей данные записываются в обе базы одновременно.
3. **Отказоустойчивость** - При недоступности одной из баз данных, система продолжит работу с доступной базой.
4. **Поддержка больших ID** - Система корректно обрабатывает большие Telegram ID (более 2^31), используя тип BIGINT в PostgreSQL.

## Структура файлов

- `dual_migrate.py` - Скрипт для миграции данных из Google Sheets в обе базы данных
- `database.py` - Основной интерфейс для работы с базами данных
- `db/postgres_client.py` - Клиент для работы с PostgreSQL
- `db/utils.py` - Утилиты для работы с базами данных

## Использование двойной миграции

### Миграция данных из Google Sheets

```bash
python dual_migrate.py --pg-db-url="postgresql://postgres:пароль@хост:порт/база" \
                     --sqlite-db-path="путь_к_sqlite_базе.db" \
                     --creds-file="путь_к_google_creds.json" \
                     --sheet-key="ключ_google_таблицы" \
                     --sheet-name="имя_листа"
```

### Параметры скрипта

- `--pg-db-url` - URL для подключения к PostgreSQL
- `--sqlite-db-path` - Путь к файлу SQLite
- `--creds-file` - Путь к файлу с учетными данными Google API
- `--sheet-key` - Ключ Google Sheets таблицы
- `--sheet-name` - Имя листа в таблице

## Работа с пользователями в двойной системе

Для добавления, обновления и чтения данных пользователей следует использовать класс `DualDatabase` из модуля `dual_database.py`, который автоматически работает с обеими базами данных.

### Пример использования DualDatabase

```python
from dual_database import DualDatabase

# Инициализация базы данных (автоматически подключится к обеим базам)
db = DualDatabase(pg_url="postgresql://postgres:пароль@хост:порт/база", sqlite_path="путь_к_sqlite_базе.db")

# Добавление пользователя (данные будут добавлены в обе базы)
user_data = {
    "user_id": 123456789,
    "username": "example_user",
    "first_name": "Пример",
    "status": "registered",
    "phone_number": "+79999999999",
    "source": "registration_form"
}
db.add_user(user_data)

# Получение данных пользователя (приоритет у PostgreSQL)
user = db.get_user(123456789)
print(f"Имя пользователя: {user.get('username')}")

# Обновление данных пользователя (в обеих базах)
update_data = {
    "real_name": "Пример Примерович",
    "profile_completed": True
}
db.update_user(123456789, update_data)

# Получение списка последних 10 пользователей
users = db.get_all_users(limit=10)
for user in users:
    print(f"ID: {user.get('user_id')}, Имя: {user.get('first_name')}")
```

## Схема таблицы users

### Структура таблицы users

| Поле                | Тип (PostgreSQL)            | Тип (SQLite)  | Описание                            |
|---------------------|----------------------------|---------------|-------------------------------------|
| id                  | integer                    | INTEGER       | Первичный ключ, автоинкремент       |
| user_id             | bigint                     | INTEGER       | ID пользователя Telegram            |
| username            | character varying          | TEXT          | Имя пользователя                    |
| first_name          | character varying          | TEXT          | Имя                                 |
| status              | character varying          | TEXT          | Статус пользователя                 |
| phone_number        | character varying          | TEXT          | Номер телефона                      |
| real_name           | character varying          | TEXT          | Настоящее имя                       |
| birth_date          | character varying          | TEXT          | Дата рождения                       |
| register_date       | timestamp without time zone| TEXT          | Дата регистрации                    |
| last_activity       | timestamp without time zone| TEXT          | Последняя активность                |
| redeem_date         | timestamp without time zone| TEXT          | Дата погашения                      |
| source              | character varying          | TEXT          | Источник                            |
| referrer_id         | bigint                     | INTEGER       | ID реферера                         |
| brought_by_staff_id | integer                    | INTEGER       | ID сотрудника, привлекшего клиента  |
| profile_completed   | boolean                    | INTEGER       | Флаг заполнения профиля             |
| ai_concept          | character varying          | TEXT          | AI концепция                        |

## Особенности и рекомендации

1. **Использование транзакций** - При добавлении данных в обе базы рекомендуется использовать транзакции для обеспечения согласованности данных.
2. **Обработка ошибок** - В случае сбоя одной из баз данных, важно корректно обрабатывать ошибки и вести журнал ошибок.
3. **Типы данных** - Обратите внимание на различия в типах данных между PostgreSQL и SQLite. Особенно это касается дат, времени и булевых значений.
4. **Большие ID** - Для корректной работы с большими Telegram ID (более 2^31), в PostgreSQL используется тип BIGINT.

## Устранение неполадок

### Проблемы с подключением к PostgreSQL

1. Проверьте корректность строки подключения
2. Убедитесь, что сервер PostgreSQL доступен
3. Проверьте наличие необходимых привилегий для пользователя

### Проблемы с SQLite

1. Проверьте права доступа к файлу базы данных
2. Убедитесь, что файл не заблокирован другим процессом
3. Проверьте наличие свободного места на диске

## Поддерживаемые версии

- PostgreSQL: 12.0 и выше
- SQLite: 3.0 и выше
- Python: 3.8 и выше
