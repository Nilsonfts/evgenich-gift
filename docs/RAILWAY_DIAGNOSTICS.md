# 🔍 Диагностика проблем с отчетами на Railway

## 🚨 Найденные и исправленные проблемы:

### 1. ❌ Неправильный импорт send_report в main.py
**Проблема**: В main.py импортировался `send_report` из `handlers.admin_panel`, но функция была перенесена в `handlers.reports`

**Исправление**: 
```python
# Было:
from handlers.admin_panel import register_admin_handlers, send_report, init_admin_handlers

# Стало:
from handlers.admin_panel import register_admin_handlers, init_admin_handlers  
from handlers.reports import send_report
```

### 2. ❌ Проблема с запуском fix_postgresql_columns.py на Railway
**Проблема**: Команда `python core/fix_postgresql_columns.py` не работала с новой структурой

**Исправление**: Создан `deployment/startup.sh` скрипт:
```bash
#!/bin/bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python core/fix_postgresql_columns.py
python main.py
```

### 3. ✅ Логика отчетов работает корректно
Функции отчетов в `handlers/reports.py` и база данных работают правильно.

## 🔧 Чтобы диагностировать проблему на Railway:

### 1. Проверьте логи Railway:
```bash
# В Railway Dashboard > Deployments > View Logs
# Ищите ошибки типа:
# - ImportError: cannot import name 'send_report'
# - ModuleNotFoundError: No module named 'core.fix_postgresql_columns'
# - Ошибки PostgreSQL подключения
```

### 2. Проверьте переменные окружения:
```bash
# Убедитесь что установлены:
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://...
CHANNEL_ID=@your_channel
ADMIN_IDS=123456789
NASTOYKA_NOTIFICATIONS_CHAT_ID=-1002813620544
REPORT_CHAT_ID=your_report_chat_id
```

### 3. Проверьте расписание отчетов:
Отчеты отправляются в **05:30 по московскому времени** в чат `NASTOYKA_NOTIFICATIONS_CHAT_ID`

### 4. Тестирование отчета вручную:
Добавьте временно в main.py:
```python
# После инициализации бота добавьте:
@bot.message_handler(commands=['test_report'])
def test_report(message):
    if message.from_user.id in ALL_ADMINS:
        from datetime import datetime, timedelta
        import pytz
        tz = pytz.timezone('Europe/Moscow')
        end_time = datetime.now(tz)
        start_time = end_time - timedelta(hours=24)
        send_report(bot, message.chat.id, start_time, end_time)
```

### 5. Проверьте права бота в чатах:
Убедитесь что бот имеет права отправлять сообщения в:
- `NASTOYKA_NOTIFICATIONS_CHAT_ID` (-1002813620544)
- `REPORT_CHAT_ID` (резервный чат)

## 🎯 Основные исправления применены:
- ✅ Импорт send_report исправлен
- ✅ Startup скрипт для Railway создан
- ✅ Все пути к модулям обновлены

Теперь отчеты должны работать корректно! 🎉
