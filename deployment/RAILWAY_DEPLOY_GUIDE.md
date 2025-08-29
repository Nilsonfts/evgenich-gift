# 🚀 Инструкция по деплою на Railway

## ✅ Готово к деплою!

Все критические ошибки исправлены:
- ✅ Импорт `send_report` исправлен в main.py
- ✅ Создан `deployment/startup.sh` для корректного запуска
- ✅ Обновлены все пути под новую структуру
- ✅ Railway конфигурация исправлена

## 🔧 Действия на Railway:

### 1. Переdeploy проекта
В Railway Dashboard:
1. Перейти в проект `evgenich-gift`
2. Нажать **"Deploy"** или **"Redeploy"**
3. Убедиться что используется файл `deployment/railway.json`

### 2. Проверить конфигурацию
Убедиться что установлены переменные:
```
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://...
CHANNEL_ID=@your_channel
NASTOYKA_NOTIFICATIONS_CHAT_ID=-1002813620544
ADMIN_IDS=123456789
```

### 3. Проверить логи
После деплоя проверить логи на наличие:
- ✅ `Инициализация PostgreSQL базы данных...`
- ✅ `Scheduler: Задача для ежедневного отчета запланирована на 05:30`
- ❌ Отсутствие ошибок ImportError

### 4. Тестирование
1. **Проверить выдачу настоек**: Новый пользователь → подписка → получение купона → погашение
2. **Проверить отчеты**: В 05:30 МСК в чат `-1002813620544`
3. **Добавить тестовую команду** (опционально):
```python
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

## 🎯 Ожидаемый результат:
- ✅ Бот запускается без ошибок
- ✅ PostgreSQL миграции выполняются  
- ✅ Отчеты отправляются по расписанию
- ✅ Выдача и погашение настоек работает

Все готово! 🎉
