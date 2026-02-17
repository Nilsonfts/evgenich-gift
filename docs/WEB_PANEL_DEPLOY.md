# Деплой Админ-панели на Railway

## Быстрый старт

### 1. Создать новый сервис в Railway
1. Откройте ваш проект на [railway.app](https://railway.app)
2. Нажмите **+ New** → **GitHub Repo** → выберите `evgenich-gift`
3. Появится второй сервис из того же репозитория

### 2. Настроить переменные окружения
В настройках нового сервиса (Settings → Variables):

| Переменная | Значение | Обязательно |
|---|---|---|
| `DATABASE_URL` | Скопируйте из сервиса бота | ✅ |
| `ADMIN_USER` | `admin` (или свой логин) | По желанию |
| `ADMIN_PASSWORD` | `Evgenich83` (или свой пароль) | ✅ |
| `FLASK_SECRET_KEY` | Любая длинная строка | Рекомендуется |
| `USE_POSTGRES` | `true` | ✅ |

> **Совет**: Если PostgreSQL уже на Railway, можно подключить ту же БД через Shared Variables.

### 3. Настроить Start Command
В настройках сервиса → **Settings** → **Deploy** → **Custom Start Command**:

```
cd /app && gunicorn web.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

Или используйте файл `web/railway.toml` — Railway автоматически его подхватит, если
указать **Root Directory** = `/` (корень репозитория).

### 4. Открыть панель
После деплоя Railway выдаст домен вида:
```
https://evgenich-gift-web-production-XXXX.up.railway.app
```

Откройте его → введите логин/пароль → готово!

---

## Альтернатива: запуск локально

```bash
cd /workspaces/evgenich-gift
pip install -r requirements.txt
python -m web.app
```

Панель будет доступна на `http://localhost:5000`

---

## Структура

```
web/
├── app.py                    ← Flask-приложение (все маршруты)
├── railway.toml              ← Конфигурация Railway
├── requirements.txt          ← Зависимости (Flask, gunicorn)
├── admin_config/             ← JSON-файлы настроек
│   ├── ai_settings.json
│   ├── bars.json
│   ├── links.json
│   ├── promotions.json
│   ├── staff.json
│   └── texts.json
└── templates_full/
    └── full/
        ├── base.html         ← Базовый layout (sidebar)
        ├── login.html        ← Страница входа
        ├── dashboard.html    ← Дашборд (метрики)
        ├── users.html        ← Список пользователей
        ├── user_detail.html  ← Профиль пользователя
        ├── analytics.html    ← Аналитика
        ├── broadcast.html    ← Рассылки
        ├── staff.html        ← Персонал
        ├── promotions.html   ← Акции
        ├── ai_settings.html  ← AI настройки
        ├── bars.html         ← Бары
        ├── texts.html        ← Тексты бота
        └── links.html        ← Внешние ссылки
```

## Разделы панели

| Раздел | Описание |
|---|---|
| **Дашборд** | Общая статистика, топ сотрудников, последние действия |
| **Пользователи** | Поиск, фильтр по статусу, профиль, купоны |
| **Аналитика** | Отчёты за период, churn analysis, воронка, рефералы |
| **Рассылки** | Статистика рассылок, инструкция по /broadcast |
| **Персонал** | Список сотрудников, роли (боссы/админы/SMM) |
| **Акции** | Групповой бонус, Happy Hours, пароль дня |
| **AI** | Промпт, модель, температура, макс. токены |
| **Бары** | CRUD заведений |
| **Тексты** | Редактор текстов бота |
| **Ссылки** | Соц. сети и контакты |
