# 🚂 ИСПРАВЛЕНИЕ: Отдельная переменная для второй таблицы

## 🎯 Проблема
Вторая таблица была пустая, потому что код пытался парсить два ключа из одной переменной `GOOGLE_SHEET_KEY`, но на Railway была настроена только основная таблица.

## ✅ Решение: Отдельная переменная

Вместо парсинга одной переменной через запятую, теперь используем **две отдельные переменные**:

### 📝 Изменения в `config.py`:

**Было:**
```python
GOOGLE_SHEET_KEY_RAW = os.getenv("GOOGLE_SHEET_KEY")
if GOOGLE_SHEET_KEY_RAW:
    GOOGLE_SHEET_KEYS = [key.strip() for key in GOOGLE_SHEET_KEY_RAW.split(',')]
    GOOGLE_SHEET_KEY = GOOGLE_SHEET_KEYS[0]  # Основная
    GOOGLE_SHEET_KEY_SECONDARY = GOOGLE_SHEET_KEYS[1]  # Дополнительная
```

**Стало:**
```python
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")                    # Основная таблица
GOOGLE_SHEET_KEY_SECONDARY = os.getenv("GOOGLE_SHEET_KEY_SECONDARY") # Дополнительная таблица
```

## 🚂 Настройка на Railway

### 1. Проверить существующую переменную:
- **Variable**: `GOOGLE_SHEET_KEY`
- **Value**: `1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs` ✅

### 2. Добавить новую переменную:
- **Variable**: `GOOGLE_SHEET_KEY_SECONDARY`
- **Value**: `1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4`

## 📊 Какие таблицы:

### Основная таблица (17 колонок A-Q):
- **Ключ**: `1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs`
- **Вкладка**: "Заявки из Соц сетей" (gid=1842872487)
- **Структура**: Полная с UTM, источниками, тегами
- **Telegram ID**: Колонка Q

### Дополнительная таблица (16 колонок A-P):
- **Ключ**: `1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4`
- **Вкладка**: "Заявки Соц сети" (gid=871899838)
- **Структура**: Упрощенная для анализа
- **Telegram ID**: Колонка P

## 🚀 Пошаговая инструкция Railway:

1. **Заходим в Railway**:
   - Открываем https://railway.app
   - Логинимся
   - Выбираем проект `evgenich-gift`

2. **Открываем Variables**:
   - Кликаем на проект
   - Переходим в вкладку **Variables**

3. **Проверяем основную переменную**:
   - Ищем `GOOGLE_SHEET_KEY`
   - Должно быть: `1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs`

4. **Добавляем новую переменную**:
   - Кликаем **New Variable**
   - **Name**: `GOOGLE_SHEET_KEY_SECONDARY`
   - **Value**: `1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4`
   - Кликаем **Add**

5. **Перезапуск**:
   - Railway автоматически перезапустит бот
   - Ждем 1-2 минуты

## 🔍 Проверка работы:

После добавления переменной в логах должно появиться:

```
✅ Найдена вкладка: Заявки Соц сети (id=871899838)
✅ Строка успешно записана в таблицу
✅ Заявка успешно экспортирована в дополнительную таблицу
```

## 💡 Преимущества:

- ✅ **Проще настройка** - две отдельные переменные
- ✅ **Больше контроля** - можно отключить одну таблицу
- ✅ **Понятнее код** - нет парсинга через запятую
- ✅ **Гибкость** - легко добавить третью таблицу

---

**После добавления переменной на Railway бот начнет дублировать заявки в обе таблицы!** 🚀
