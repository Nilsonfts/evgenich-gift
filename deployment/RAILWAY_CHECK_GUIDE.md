# 🔍 Чек-лист для проверки Railway

## ✅ Что искать в логах деплоя:

### 1. **Успешный старт:**
```
✅ Инициализация PostgreSQL базы данных...
✅ PostgreSQL URL: [адрес без пароля]
✅ Scheduler: Задача для ежедневного отчета запланирована на 05:30
✅ Bot запущен успешно!
```

### 2. **Возможные ошибки:**
```
❌ ImportError: cannot import name 'send_report'
❌ ModuleNotFoundError: No module named 'core.config'
❌ ValueError: Основные переменные окружения не установлены
❌ psycopg2.OperationalError: connection failed
```

## 🔧 Если видите ошибки:

### ImportError/ModuleNotFoundError:
- Убедитесь что Railway использует `deployment/railway.json`
- Проверьте что `startCommand` указывает на `bash deployment/startup.sh`

### Переменные окружения:
Убедитесь что установлены:
```
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://...
CHANNEL_ID=@your_channel
ADMIN_IDS=123456789
NASTOYKA_NOTIFICATIONS_CHAT_ID=-1002813620544
```

### PostgreSQL ошибки:
- Проверьте что DATABASE_URL корректный
- Убедитесь что PostgreSQL сервис запущен в Railway

## 📱 Тестирование бота:

1. **Найдите бота в Telegram** по имени
2. **Отправьте /start** - должно прийти приветствие
3. **Попробуйте получить настойку** - весь флоу должен работать
4. **Проверьте отчеты в 05:30 МСК** в чате -1002813620544

## 🚨 Критические команды для проверки:

```bash
# Railway CLI команды:
railway logs --tail       # Живые логи
railway status            # Статус деплоя  
railway variables         # Переменные окружения
railway redeploy          # Повторный деплой
```

## 📊 Ожидаемое поведение:

- ✅ Бот отвечает на /start
- ✅ Выдает купоны подписчикам канала
- ✅ Погашает купоны (обновляет статус в БД)
- ✅ Отправляет отчеты в 05:30 МСК
- ✅ Админы могут использовать /admin
