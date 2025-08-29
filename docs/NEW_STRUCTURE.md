# 📁 Новая структура проекта "Квартира Евгенича"

После реорганизации проект имеет следующую улучшенную структуру:

## 🗂️ Структура папок

```
evgenich-gift/
├── 📁 core/                    # Основная логика системы
│   ├── config.py              # Конфигурация и настройки
│   ├── database.py            # Работа с базой данных
│   ├── dual_database.py       # Двойная система БД
│   ├── fix_postgresql_columns.py  # Миграции PostgreSQL
│   ├── delayed_tasks_processor.py  # Обработка отложенных задач
│   └── settings_manager.py    # Управление настройками
│
├── 📁 handlers/               # Обработчики команд и событий
│   ├── __init__.py
│   ├── admin_panel.py         # Админ-панель
│   ├── ai_logic.py           # ИИ-логика
│   ├── booking_flow.py       # Поток бронирования
│   ├── broadcast.py          # Рассылки
│   ├── callback_query.py     # Обработка callback'ов
│   ├── content.py            # Контент
│   ├── iiko_data_handler.py  # Обработка данных iiko
│   ├── newsletter_*.py       # Управление рассылками
│   ├── promotions.py         # Акции и промо
│   ├── reports*.py           # Отчёты
│   ├── staff.py              # Персонал
│   ├── user_commands.py      # Команды пользователей
│   ├── users.py              # Пользователи
│   ├── utils.py              # Утилиты обработчиков
│   └── steps/                # Пошаговые процессы
│       └── admin_steps.py
│
├── 📁 keyboards/              # Клавиатуры и кнопки
│   ├── __init__.py           # Основные клавиатуры (перенесён keyboards.py)
│   ├── admin.py              # Админские клавиатуры
│   ├── common.py             # Общие клавиатуры
│   └── user.py               # Пользовательские клавиатуры
│
├── 📁 texts/                  # Тексты сообщений
│   ├── __init__.py           # Основные тексты (перенесён texts.py)
│   ├── admin.py              # Админские тексты
│   ├── common.py             # Общие тексты
│   └── user.py               # Пользовательские тексты
│
├── 📁 ai/                     # ИИ и знания
│   ├── assistant.py          # ИИ-ассистент
│   ├── knowledge.py          # База знаний
│   └── knowledge_base.py     # Расширенная база знаний
│
├── 📁 modules/                # Функциональные модули
│   ├── daily_activities.py   # Ежедневные активности
│   ├── games.py              # Игры и развлечения
│   ├── food_menu.py          # Меню еды
│   ├── marketing_templates.py # Маркетинговые шаблоны
│   ├── menu_nastoiki.py      # Меню настоек
│   └── staff_manager.py      # Управление персоналом
│
├── 📁 utils/                  # Утилиты и вспомогательные функции
│   ├── export_to_sheets.py   # Экспорт в Google Sheets
│   ├── qr_generator.py       # Генератор QR-кодов
│   ├── referral_notifications.py  # Реферальные уведомления
│   └── social_bookings_export.py  # Экспорт бронирований
│
├── 📁 web/                    # Веб-интерфейс
│   ├── web_app.py            # Flask приложение
│   ├── web_requirements.txt  # Зависимости для веба
│   └── templates/            # HTML шаблоны
│       ├── analytics.html
│       ├── base.html
│       ├── dashboard.html
│       └── users.html
│
├── 📁 deployment/             # Конфигурация деплоя
│   ├── Procfile              # Heroku/Railway старт
│   ├── railway.json          # Настройки Railway (бот)
│   ├── web.railway.json      # Настройки Railway (веб)
│   ├── web.Dockerfile        # Docker для веба
│   ├── railway-start.sh      # Скрипт запуска Railway
│   └── start_web.sh          # Локальный запуск веба
│
├── 📁 db/                     # Работа с базами данных
│   ├── migrate_helpers.py    # Помощники миграций
│   └── postgres_client.py    # PostgreSQL клиент
│
├── 📁 docs/                   # Документация
│   └── DUAL_DATABASE_SYSTEM.md
│
├── 📁 logs/                   # Логи (создаётся автоматически)
│   └── README.md
│
├── main.py                    # 🚀 Главный файл запуска
├── requirements.txt           # Python зависимости
├── README.md                 # Документация проекта
└── CONTRIBUTING.md           # Руководство участника
```

## 🔧 Что изменилось

### ✅ Удалены ненужные файлы:
- `demo_report.py` - демо-файл отчётов
- `find_google_sheets.py` - поиск Google Sheets
- `create_google_sheet.py` - создание Google Sheets
- `image/` - неиспользуемая папка с изображениями

### 📦 Реорганизованы файлы:
- **Основная логика** → `core/`
- **Игры и функции** → `modules/`
- **Утилиты** → `utils/`
- **Веб-интерфейс** → `web/`
- **Деплой** → `deployment/`
- **ИИ** → `ai/`

### 🔄 Обновлены импорты:
- `from config import` → `from core.config import`
- `import database` → `import core.database as database`
- `from games import` → `from modules.games import`
- `from qr_generator import` → `from utils.qr_generator import`
- И так далее...

### 🚀 Обновлены скрипты деплоя:
- Railway команды обновлены для новой структуры
- Docker файлы исправлены
- Startup скрипты адаптированы

## 💡 Преимущества новой структуры

1. **🎯 Логическое разделение** - каждая папка имеет четкое назначение
2. **🔍 Лёгкость навигации** - быстро найти нужный файл
3. **🛠️ Удобство разработки** - модульность кода
4. **📈 Масштабируемость** - легко добавлять новые модули
5. **🧹 Чистота кода** - убраны ненужные файлы

## 🚀 Запуск проекта

### Локально:
```bash
python main.py  # Запуск бота
bash deployment/start_web.sh  # Запуск веб-интерфейса
```

### На Railway:
- Основной бот: использует `deployment/railway.json`
- Веб-интерфейс: использует `deployment/web.railway.json`

Структура теперь готова к продакшену и легко поддерживается! 🎉
