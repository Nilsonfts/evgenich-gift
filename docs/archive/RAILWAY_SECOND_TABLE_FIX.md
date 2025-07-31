# 🔧 ИСПРАВЛЕНИЕ: Настройка второй таблицы на Railway

## 🚨 Проблема
Данные не выгружаются во вторую таблицу, потому что на Railway не настроен ключ дополнительной таблицы.

## 📊 Диагностика
Код пытается получить `GOOGLE_SHEET_KEY_SECONDARY` из второго ключа в переменной `GOOGLE_SHEET_KEY`, но там указан только один ключ.

## ✅ Решение

### 1. Текущее значение GOOGLE_SHEET_KEY на Railway:
```
1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs
```

### 2. Нужно изменить на:
```
1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs,1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4
```

### 3. Где:
- **Первый ключ** (`1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs`) - основная таблица
- **Второй ключ** (`1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4`) - дополнительная таблица

## 🚂 Пошаговая инструкция для Railway:

1. **Заходим в Railway Dashboard**: https://railway.app/
2. **Выбираем проект**: evgenich-gift
3. **Переходим в Variables** (вкладка переменных окружения)
4. **Находим переменную**: `GOOGLE_SHEET_KEY`
5. **Текущее значение**: `1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs`
6. **Изменяем на**: `1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs,1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4`

   ⚠️ **ВАЖНО**: Между ключами ставим запятую без пробелов!

7. **Сохраняем изменения**
8. **Railway автоматически перезапустит бот** с новыми настройками

## 🔍 Проверка после исправления:

После изменения переменной на Railway в логах бота должны появиться записи:
```
✅ Заявка успешно экспортирована в дополнительную таблицу. Клиент: ИмяКлиента, TG ID: 123456789
```

Вместо:
```
❌ Дополнительная таблица не настроена - GOOGLE_SHEET_KEY_SECONDARY отсутствует
```

## 📋 Ссылки на таблицы:

1. **Основная таблица "Заявки из Соц сетей"**: 
   https://docs.google.com/spreadsheets/d/1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs/edit?gid=1842872487

2. **Дополнительная таблица "Заявки Соц сети"**: 
   https://docs.google.com/spreadsheets/d/1QL1CRY3M9Av-WlDS5gswA2Lq14OPdt0TME_dpwPIuC4/edit?gid=871899838

## 🎯 Ожидаемый результат:

После исправления каждая заявка будет дублироваться в обе таблицы:
- **Основная таблица**: 17 колонок (A-Q) - полная информация
- **Дополнительная таблица**: 16 колонок (A-P) - упрощенная структура

---

**🚀 После этого исправления дублирующий экспорт заработает!**
