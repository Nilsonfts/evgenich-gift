# ПОЛНЫЙ АУДИТ INLINE-КНОПОК И CALLBACK-ОБРАБОТЧИКОВ

**Дата аудита:** 20.02.2026  
**Проект:** evgenich-gift (Telegram Bot, pyTeleBot)

---

## 1. ПОРЯДОК РЕГИСТРАЦИИ ОБРАБОТЧИКОВ (main.py)

В pyTeleBot **первый** подходящий `callback_query_handler` обрабатывает callback. Порядок:

```
1.  register_chat_booking_handlers(bot)          — БЕЗ callback_query_handler
2.  register_user_command_handlers(bot)           — staff_reg_pos_*
3.  register_callback_handlers(bot, ...)          — CATCH-ALL для пользовательских кнопок
4.  register_booking_handlers(bot)                — source_*, bar_*, booking_*, confirm/cancel_booking
5.  init_admin_handlers(bot, scheduler):
      → register_newsletter_handlers(bot, sched)  — admin_content_*, admin_newsletter_*, admin_button_*
      → register_newsletter_buttons_handlers(bot)  — admin_button_*, newsletter_click_*
6.  register_admin_handlers(bot)                  — admin_*/boss_* CATCH-ALL (с исключениями)
7.  register_content_handlers(bot)                — БЕЗ callback_query_handler (только /commands)
8.  register_proactive_commands(bot)              — БЕЗ callback_query_handler
9.  register_broadcast_handlers(bot)              — broadcast_*
10. register_ai_handlers(bot)                     — БЕЗ callback_query_handler
11. register_iiko_data_handlers(bot)              — БЕЗ callback_query_handler
```

---

## 2. ВСЕ CALLBACK_QUERY_HANDLER С ФИЛЬТРАМИ

| #  | Файл | Фильтр | Функция |
|----|-------|--------|---------|
| H1 | handlers/user_commands.py:374 | `call.data.startswith("staff_reg_pos_")` | `handle_staff_position_choice` |
| H2 | handlers/callback_query.py:28 | `NOT (admin_* OR boss_* OR booking_* OR source_* OR bar_* OR broadcast_* OR newsletter_click_* OR confirm_booking OR cancel_booking)` | `handle_all_callbacks` (пользовательский catch-all) |
| H3 | handlers/booking_flow.py:103 | `call.data.startswith("source_")` | `handle_traffic_source_callback` |
| H4 | handlers/booking_flow.py:134 | `call.data.startswith("bar_")` | `handle_bar_selection_callback` |
| H5 | handlers/booking_flow.py:185 | `call.data.startswith("booking_")` | `handle_booking_option_callback` |
| H6 | handlers/booking_flow.py:222 | `call.data in ["confirm_booking", "cancel_booking"]` | `handle_booking_confirmation_callback` |
| H7 | handlers/newsletter_manager.py:25 | `call.data.startswith('admin_content_')` | `handle_content_callbacks` (NewsletterManager) |
| H8 | handlers/newsletter_manager.py:43 | `call.data.startswith('admin_newsletter_')` | `handle_newsletter_callbacks` (NewsletterManager) |
| H9 | handlers/newsletter_manager.py:74 | `call.data.startswith('admin_button_')` | `handle_button_callbacks` (NewsletterManager) |
| H10 | handlers/newsletter_buttons.py:21 | `call.data.startswith('admin_button_')` | `handle_button_callbacks` (NewsletterButtonsManager) |
| H11 | handlers/newsletter_buttons.py:48 | `call.data.startswith('newsletter_click_')` | `handle_newsletter_button_clicks` |
| H12 | handlers/admin_panel.py:418 | `(admin_* OR boss_*) AND NOT startswith(_newsletter_prefixes)` | `handle_admin_callbacks` (админ catch-all) |
| H13 | handlers/broadcast.py:42 | `call.data.startswith('broadcast_')` | `on_broadcast_callback` |

**Исключения admin_panel (_newsletter_prefixes):**
```
admin_newsletter_type_, admin_newsletter_test_, admin_newsletter_send_,
admin_newsletter_schedule_, admin_newsletter_view_, admin_newsletter_stats_,
admin_newsletter_ready_, admin_newsletter_edit_, admin_newsletter_delete_,
admin_newsletter_send_menu_, admin_newsletter_add_button_, admin_newsletter_buttons_,
admin_button_
```

---

## 3. ВСЕ CALLBACK_DATA ЗНАЧЕНИЯ И МАРШРУТИЗАЦИЯ

### 3.1 Пользовательские кнопки (keyboards/__init__.py + utils/)

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `check_subscription` | keyboards/__init__.py:62 | **H2** → handle_check_subscription | ✅ OK |
| `redeem_reward` | keyboards/__init__.py:69 | **H2** → handle_redeem_reward | ✅ OK |
| `concept_<name>` | keyboards/__init__.py:84 (динамич.) | **H2** → callback_concept_choice | ✅ OK |
| `start_booking` | handlers/callback_query.py:334 | **H2** → handle_start_booking_callback | ✅ OK |
| `feedback_<rating>` | (генерируется в коде) | **H2** → handle_feedback_rating | ✅ OK |
| `quiz_answer_<q>_<a>` | handlers/user_commands.py:1029 | **H2** → callback_quiz_answer | ✅ OK |
| `check_referral_rewards` | handlers/user_commands.py:504 | **H2** → handle_check_referral_rewards | ✅ OK |
| `claim_reward` | utils/referral_notifications.py:52 | **H2** → handle_claim_reward_callback | ✅ OK |
| `show_referral_link` | utils/referral_notifications.py:160 | **H2** → handle_show_referral_link | ✅ OK |
| `show_referral_stats` | utils/referral_notifications.py:239 | **H2** → handle_show_referral_stats | ✅ OK |

### 3.2 Кнопки бронирования

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `booking_bot` | keyboards/__init__.py:94 | **H5** | ✅ OK |
| `booking_phone` | keyboards/__init__.py:95 | **H5** | ✅ OK |
| `booking_site` | keyboards/__init__.py:96 | **H5** | ✅ OK |
| `booking_secret` | (нет в keyboards, есть handler) | **H5** | ⚠️ Обработчик есть, кнопка не найдена |
| `confirm_booking` | keyboards/__init__.py:103,157 | **H6** | ✅ OK |
| `cancel_booking` | keyboards/__init__.py:104,157 | **H6** | ✅ OK |
| `source_vk` | keyboards/__init__.py:129 | **H3** | ✅ OK |
| `source_inst` | keyboards/__init__.py:130 | **H3** | ✅ OK |
| `source_bot_tg` | keyboards/__init__.py:133 | **H3** | ✅ OK |
| `source_tg` | keyboards/__init__.py:134 | **H3** | ✅ OK |
| `bar_<callback_id>` | keyboards/__init__.py:149 (динамич.) | **H4** | ✅ OK |

### 3.3 Регистрация персонала

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `staff_reg_pos_Официант` | keyboards/__init__.py:279 | **H1** | ✅ OK |
| `staff_reg_pos_Бармен` | keyboards/__init__.py:280 | **H1** | ✅ OK |
| `staff_reg_pos_Менеджер` | keyboards/__init__.py:281 | **H1** | ✅ OK |

### 3.4 Админ-панель — навигация

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `admin_main_menu` | keyboards/__init__.py:203,221,232,242,251,260,299 | **H12** | ✅ OK |
| `admin_menu_promotions` | keyboards/__init__.py:167 | **H12** | ✅ OK |
| `admin_menu_reports` | keyboards/__init__.py:168 | **H12** | ✅ OK |
| `admin_menu_content` | keyboards/__init__.py:169 | **H12** | ✅ OK |
| `admin_menu_broadcasts` | keyboards/__init__.py:170 | **H12** | ✅ OK |
| `admin_menu_staff` | keyboards/__init__.py:171 | **H12** | ✅ OK |
| `admin_menu_users` | keyboards/__init__.py:172 | **H12** | ✅ OK |
| `admin_menu_data` | keyboards/__init__.py:173 | **H12** | ✅ OK |

### 3.5 Админ — управление акциями

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `boss_toggle_promotions.group_bonus.is_active` | keyboards/__init__.py:185 | **H12** | ✅ OK |
| `boss_toggle_promotions.happy_hours.is_active` | keyboards/__init__.py:192 | **H12** | ✅ OK |
| `boss_toggle_promotions.password_of_the_day.is_active` | keyboards/__init__.py:199 | **H12** | ✅ OK |
| `boss_set_password` | keyboards/__init__.py:229 | **H12** | ✅ OK |
| `boss_upload_audio` | keyboards/__init__.py:230 | **H12** | ✅ OK |

### 3.6 Админ — отчёты и аналитика

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `admin_report_current_shift` | keyboards/__init__.py:210 | **H12** | ✅ OK |
| `admin_report_manual_daily` | keyboards/__init__.py:211 | **H12** | ✅ OK |
| `admin_report_full_statistics` | keyboards/__init__.py:212 | **H12** | ✅ OK |
| `admin_report_staff_realtime` | keyboards/__init__.py:213 | **H12** | ✅ OK |
| `admin_staff_qr_diagnostics` | keyboards/__init__.py:214 | **H12** | ✅ OK |
| `admin_report_leaderboard` | keyboards/__init__.py:215 | **H12** | ✅ OK |
| `admin_churn_analysis` | keyboards/__init__.py:216 | **H12** | ✅ OK |
| `admin_report_source_funnel` | keyboards/__init__.py:217 | **H12** | ✅ OK |
| `admin_report_churn_by_source` | keyboards/__init__.py:218 | **H12** | ✅ OK |
| `admin_report_activity_time` | keyboards/__init__.py:219 | **H12** | ✅ OK |

### 3.7 Админ — управление пользователями/персоналом/данными

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `admin_find_user` | keyboards/__init__.py:239 | **H12** | ✅ OK |
| `admin_issue_coupon_manual` | keyboards/__init__.py:240 | **H12** | ✅ OK |
| `admin_export_sheets` | keyboards/__init__.py:249 | **H12** | ✅ OK |
| `admin_list_staff` | keyboards/__init__.py:258 | **H12** | ✅ OK |
| `admin_toggle_staff_<id>_<status>` | keyboards/__init__.py:271 (динамич.) | **H12** | ✅ OK |

### 3.8 Система рассылок (newsletter) — ❗ ПРОБЛЕМНАЯ ЗОНА

| callback_data | Где создаётся | Перехватывает | Обрабатывает? | Статус |
|---|---|---|---|---|
| `admin_newsletter_main` | keyboards/__init__.py:228 | **H8** (newsletter_manager) | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_newsletter_template_choice` | keyboards/__init__.py:395 | **H8** (newsletter_manager) | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_newsletter_custom_choice` | keyboards/__init__.py:396 | **H8** (newsletter_manager) | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_newsletter_type_text` | keyboards/__init__.py:424 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_type_photo` | keyboards/__init__.py:425 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_type_video` | keyboards/__init__.py:426 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_test_<id>` | keyboards/__init__.py:307 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_send_<id>` | keyboards/__init__.py:308 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_schedule_<id>` | keyboards/__init__.py:309 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_view_<id>` | keyboards/__init__.py:351 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_stats_<id>` | keyboards/__init__.py:370 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_ready_<id>` | keyboards/__init__.py:321 | **H8** | ✅ | ✅ OK |
| `admin_newsletter_send_menu_<id>` | keyboards/__init__.py:366 | **H8** | ⚠️ НЕПРАВИЛЬНО | 🔴 **БАГ** |
| `admin_newsletter_edit_<id>` | keyboards/__init__.py:365 | **H8** | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_newsletter_delete_<id>` | keyboards/__init__.py:371 | **H8** | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_newsletter_add_button_<id>` | keyboards/__init__.py:320 | **H8** | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_newsletter_buttons_<id>` | keyboards/__init__.py:334 | **H8** | ❌ НЕТ! | 🔴 **СЛОМАНА** |
| `admin_content_stats` | keyboards/__init__.py:291 | **H7** | ✅ | ✅ OK |
| `admin_content_create` | keyboards/__init__.py:292,416,429 | **H7** | ✅ (но другой результат чем в admin_panel) | ⚠️ МЕЛКИЙ |
| `admin_content_list` | keyboards/__init__.py:295 | **H7** | ✅ | ✅ OK |
| `admin_content_analytics` | keyboards/__init__.py:296 | **H7** | ✅ | ✅ OK |

### 3.9 Кнопки рассылок (admin_button_*)

| callback_data | Где создаётся | Перехватывает | Статус |
|---|---|---|---|
| `admin_button_template_<id>_booking` | keyboards/__init__.py:329 | **H9** (newsletter_manager) | ✅ OK |
| `admin_button_template_<id>_website` | keyboards/__init__.py:330 | **H9** | ✅ OK |
| `admin_button_template_<id>_custom` | keyboards/__init__.py:331 | **H9** | ✅ OK |

**Примечание:** H10 (newsletter_buttons.py) тоже ловит `admin_button_*`, но H9 всегда побеждает.

### 3.10 Шаблоны рассылок (admin_template_*)

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `admin_template_promo` | keyboards/__init__.py:407 | **H12** | ✅ OK |
| `admin_template_menu` | keyboards/__init__.py:408 | **H12** | ✅ OK |
| `admin_template_event` | keyboards/__init__.py:411 | **H12** | ✅ OK |
| `admin_template_booking` | keyboards/__init__.py:412 | **H12** | ✅ OK |
| `admin_template_welcome` | keyboards/__init__.py:415 | **H12** | ✅ OK |
| `admin_use_template_<cat>` | keyboards/__init__.py:447 | **H12** | ✅ OK |
| `admin_edit_template_<cat>` | keyboards/__init__.py:448 | **H12** | ✅ OK |

### 3.11 Broadcast (рассылки босса)

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `broadcast_create` | keyboards/__init__.py:437, admin_panel.py:588 | **H13** | ✅ OK |
| `broadcast_stats` | keyboards/__init__.py:438 | **H13** | ✅ OK |
| `broadcast_text` | admin_panel.py:540, broadcast.py:296 | **H13** | ✅ OK |
| `broadcast_media` | admin_panel.py:541, broadcast.py:297 | **H13** | ✅ OK |
| `broadcast_cancel` | admin_panel.py:545, broadcast.py:136,300,331 | **H13** | ✅ OK |
| `broadcast_confirm` | broadcast.py:135 | **H13** | ✅ OK |
| `broadcast_test` | broadcast.py:320 | **H13** | ✅ OK |
| `broadcast_send_all` | broadcast.py:321 | **H13** | ✅ OK |
| `broadcast_add_button` | broadcast.py:327 | **H13** | ✅ OK |
| `broadcast_remove_button` | broadcast.py:329 | **H13** | ✅ OK |

### 3.12 Клики по кнопкам в рассылках

| callback_data | Где создаётся | Обработчик | Статус |
|---|---|---|---|
| `newsletter_click_<id>_<btn_id>` | (генерируется при создании рассылки) | **H11** | ✅ OK |

---

## 4. 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### BUG #1: `admin_newsletter_main` — кнопка «Система рассылок» НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:228` → `callback_data="admin_newsletter_main"`
- **Перехватывает:** H8 (newsletter_manager, фильтр `admin_newsletter_*`)
- **Проблема:** В newsletter_manager нет обработки для `admin_newsletter_main`. Код для обработки есть в admin_panel.py:466, но H8 перехватывает callback раньше H12.
- **Результат:** При нажатии кнопки "📧 Система рассылок" в разделе контента ничего не происходит.

### BUG #2: `admin_newsletter_template_choice` — кнопка «Использовать шаблон» НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:395` → `callback_data="admin_newsletter_template_choice"`
- **Перехватывает:** H8 (newsletter_manager)
- **Проблема:** Нет обработки в newsletter_manager. Код есть в admin_panel.py:513, но не достигается.
- **Результат:** Кнопка не реагирует.

### BUG #3: `admin_newsletter_custom_choice` — кнопка «Создать свой» НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:396` → `callback_data="admin_newsletter_custom_choice"`
- **Перехватывает:** H8 (newsletter_manager)
- **Проблема:** Аналогично BUG #2. Код обработки в admin_panel.py:523 недостижим.

### BUG #4: `admin_newsletter_send_menu_<id>` — кнопка «Отправить» ОТПРАВЛЯЕТ ВМЕСТО ПОКАЗА МЕНЮ

- **Кнопка:** `keyboards/__init__.py:366` → `callback_data="admin_newsletter_send_menu_{id}"`
- **Перехватывает:** H8, условие `action.startswith('admin_newsletter_send_')`
- **Проблема:** `admin_newsletter_send_menu_5` начинается с `admin_newsletter_send_`, поэтому попадает в ветку немедленной отправки `_send_newsletter_immediately()` вместо показа меню.
- **Результат:** 🚨 **Нажатие кнопки "Отправить" на просмотре рассылки НЕМЕДЛЕННО ОТПРАВЛЯЕТ её ВСЕМ пользователям без подтверждения!**

### BUG #5: `admin_newsletter_edit_<id>` — кнопка «Редактировать» НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:365`
- **Перехватывает:** H8 (newsletter_manager)
- **Проблема:** Нет обработки в newsletter_manager. Исключена из admin_panel's catch-all через `_newsletter_prefixes`.
- **Результат:** Кнопка не реагирует.

### BUG #6: `admin_newsletter_delete_<id>` — кнопка «Удалить» НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:371`
- **Перехватывает:** H8 (newsletter_manager)
- **Проблема:** Аналогично BUG #5.

### BUG #7: `admin_newsletter_add_button_<id>` — кнопка «Добавить кнопку» НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:320`
- **Перехватывает:** H8 (newsletter_manager)
- **Проблема:** Не обрабатывается в newsletter_manager. Предназначена для newsletter_buttons (H10), но H8 перехватывает раньше.

### BUG #8: `admin_newsletter_buttons_<id>` — кнопка «Назад» (к кнопкам рассылки) НЕ РАБОТАЕТ

- **Кнопка:** `keyboards/__init__.py:334`
- **Перехватывает:** H8 (newsletter_manager)
- **Проблема:** Аналогично BUG #7.

---

## 5. ⚠️ КОНФЛИКТЫ ОБРАБОТЧИКОВ

### КОНФЛИКТ #1: `admin_button_*` зарегистрирован ДВАЖДЫ

- **H9** (newsletter_manager.py:74) — зарегистрирован ПЕРВЫМ
- **H10** (newsletter_buttons.py:21) — зарегистрирован ВТОРЫМ
- **Последствие:** H10 (NewsletterButtonsManager) **НИКОГДА не вызывается** для `admin_button_*`. Весь его код — мёртвый.
- При этом H9 обрабатывает только `admin_button_template_*`, а H10 содержит расширенную логику (add_, finish_, skip_).

### КОНФЛИКТ #2: `newsletter_click_*` — работает, но логика разделена

- **H11** (newsletter_buttons.py:48) обрабатывает클ики — работает корректно.
- callback_query.py:28 исключает `newsletter_click_*` — корректно.

### КОНФЛИКТ #3: `admin_content_create` — разное поведение

- **H7** (newsletter_manager) вызывает `_start_newsletter_creation()` → показывает `get_newsletter_creation_menu()` (выбор типа: текст/фото/видео)
- **H12** (admin_panel) содержит код для показа `get_newsletter_creation_choice_menu()` (выбор: шаблон или свой)
- **Последствие:** Кнопка "✉️ Создать рассылку" пропускает экран выбора "шаблон/свой текст" и сразу показывает выбор типа медиа.

### КОНФЛИКТ #4: `broadcast_create` / `broadcast_stats` — мёртвый код в admin_panel

- Эти callbacks создаются в admin_panel.py:537-538 и обрабатываются там же (строки 534, 561), но `broadcast_*` **не начинается с** `admin_` или `boss_`, поэтому фильтр admin_panel **никогда не пропустит** их.
- Фактически обрабатываются H13 (broadcast.py) — работает корректно.

---

## 6. МЁРТВЫЙ КОД (файлы с обработчиками, которые НИКОГДА не регистрируются)

| Файл | Функция | Проблема |
|------|---------|----------|
| handlers/content.py | `handle_content_callbacks()` | Функция определена, но НИГДЕ не вызывается. Обработка `boss_upload_audio` и `boss_set_password` дублирована в admin_panel.py |
| handlers/promotions.py | `handle_promotions_callbacks()` | НИГДЕ не вызывается. `boss_toggle_*` обрабатывается admin_panel.py |
| handlers/reports_callbacks.py | `handle_report_callbacks()` | НИГДЕ не вызывается. `admin_report_*` обрабатывается admin_panel.py |
| handlers/users.py | `handle_user_callbacks()` | НИГДЕ не вызывается. `admin_find_user` обрабатывается admin_panel.py |
| handlers/staff.py | `handle_staff_callbacks()` | НИГДЕ не вызывается. `admin_list_staff` / `admin_toggle_staff_*` обрабатываются admin_panel.py |

---

## 7. ОБЩАЯ СВОДКА

| Метрика | Количество |
|---------|------------|
| Всего уникальных callback_data паттернов | ~75+ (включая динамические) |
| Всего callback_query_handler | 13 |
| ✅ Работают корректно | ~60 |
| 🔴 Сломанные кнопки (есть кнопка, не работает) | **8** |
| ⚠️ Конфликты обработчиков | **4** |
| Мёртвый код (файлы с неиспользуемыми обработчиками) | **5 файлов** |

---

## 8. РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ

### Приоритет 1 (КРИТИЧНО — кнопки не работают):

**Корневая причина всех багов #1-#8:** обработчик `H8` в newsletter_manager.py ловит **ВСЁ** с префиксом `admin_newsletter_`, но обрабатывает только часть. Варианты исправления:

**Вариант А (рекомендуемый):** Добавить в newsletter_manager.py обработку недостающих callback_data:
```python
# В handle_newsletter_callbacks (H8):
if action == 'admin_newsletter_main':
    # Показать меню системы рассылок
elif action == 'admin_newsletter_template_choice':
    # Показать выбор шаблонов
elif action == 'admin_newsletter_custom_choice':
    # Показать выбор типа контента
elif action.startswith('admin_newsletter_send_menu_'):
    # ВАЖНО: проверять ДО admin_newsletter_send_!
    newsletter_id = int(action.split('_')[-1])
    self._show_newsletter_sending_menu(call.message, newsletter_id)
elif action.startswith('admin_newsletter_edit_'):
    # Реализовать редактирование
elif action.startswith('admin_newsletter_delete_'):
    # Реализовать удаление
elif action.startswith('admin_newsletter_add_button_'):
    # Переадресовать к newsletter_buttons
elif action.startswith('admin_newsletter_buttons_'):
    # Переадресовать к newsletter_buttons
```

**ВАЖНО для BUG #4:** Порядок проверки `startswith` критичен! `admin_newsletter_send_menu_` ДОЛЖЕН проверяться ДО `admin_newsletter_send_`.

**Вариант Б:** Сузить фильтр H8 до конкретных префиксов, чтобы остальные callback_data пропускались к admin_panel.

### Приоритет 2 (дублирование H9/H10):

Объединить логику `admin_button_*` в один обработчик или удалить регистрацию в newsletter_manager.py (H9) и оставить только newsletter_buttons.py (H10).

### Приоритет 3 (мёртвый код):

Удалить или интегрировать файлы content.py, promotions.py, reports_callbacks.py, users.py, staff.py — их обработчики никогда не регистрируются, вся логика уже в admin_panel.py.
