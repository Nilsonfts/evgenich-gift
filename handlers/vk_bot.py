# /handlers/vk_bot.py
"""
ВКонтакте: личные сообщения сообщества → сценарий брони столика.

Обработчик принимает event-payload из Callback API VK (через web/app.py:/vk/callback),
сам отвечает гостю через VK API, по завершении сценария шлёт уведомление в
Telegram-чат менеджеров (BOOKING_NOTIFICATIONS_CHAT_ID_MSK) прямым HTTPS-запросом
к Bot API — поэтому модуль работает в Web-процессе, отдельно от main.py-бота.

Состояние сессии хранится в TinyDB (`data/vk_booking_data.json`) — отдельный файл,
чтобы не конфликтовать с Telegram-сессиями в `booking_data.json`.

Сценарий:
    bar → date → time → guests → name → phone → confirm
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import requests
from tinydb import Query, TinyDB

# VK-обработчик читает все секреты НАПРЯМУЮ из os.environ.
# Это намеренно: web-сервис может не иметь TELEGRAM-переменных (CHANNEL_ID, ADMIN_IDS,
# стикеры), которые core/config.py требует обязательно. Тогда `from core.config import ...`
# бросит ValueError на этапе импорта и весь VK-функционал не поднимется.
VK_ENABLED = os.getenv("VK_ENABLED", "false").lower() in ("true", "1", "yes")
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN", "")
VK_CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN", "")
VK_SECRET_KEY = os.getenv("VK_SECRET_KEY", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Чат МСК-броней — хардкод (как в core/config.py), уведомления летят сюда
BOOKING_NOTIFICATIONS_CHAT_ID_MSK = -1003120803112
REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID")

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Хранилище сессий
# ──────────────────────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "vk_booking_data.json",
)
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
_db = TinyDB(_DB_PATH)
_Session = Query()
_db_lock = threading.RLock()  # TinyDB не потокобезопасен

# Отдельная таблица для сохранённых контактов гостей (не сессии).
# Запоминаем имя/телефон после первой брони — при следующей просто подставляем.
_contacts_table = _db.table("contacts")
_Contact = Query()

# Дополнительный лок на user_id — предотвращает параллельную обработку
# двух одновременных событий от одного пользователя (race condition).
_user_locks: dict[int, threading.Lock] = {}
_user_locks_lock = threading.Lock()

def _get_user_lock(vk_user_id: int) -> threading.Lock:
    with _user_locks_lock:
        lock = _user_locks.get(vk_user_id)
        if lock is None:
            lock = threading.Lock()
            _user_locks[vk_user_id] = lock
        return lock

# Дедупликация event_id от VK (Callback API повторяет события, если не получил
# 'ok' за 10 секунд). Храним последние 1000 event_id ~30 минут.
import collections as _collections
_seen_events: _collections.OrderedDict = _collections.OrderedDict()
_seen_events_lock = threading.Lock()
_SEEN_EVENTS_MAX = 1000

def _is_duplicate_event(event_id: str) -> bool:
    """True, если этот event_id уже обрабатывался."""
    if not event_id:
        return False
    with _seen_events_lock:
        if event_id in _seen_events:
            return True
        _seen_events[event_id] = True
        # LRU: выкидываем самые старые
        while len(_seen_events) > _SEEN_EVENTS_MAX:
            _seen_events.popitem(last=False)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Конфигурация баров (только МСК — Пятницкая и Цветной)
# ──────────────────────────────────────────────────────────────────────────────
BARS = [
    {"key": "pyatnitskaya", "label": "🏛 Пятницкая 30",   "name": "Москва, Пятницкая 30",   "code": "ЕВГ_МСК_ПЯТ"},
    {"key": "tsvetnoj",     "label": "🌸 Цветной бульвар", "name": "Москва, Цветной бульвар", "code": "ЕВГ_МСК_ЦВЕТ"},
]
_BAR_BY_KEY = {b["key"]: b for b in BARS}
_BAR_BY_LABEL = {b["label"].lower(): b for b in BARS}

# ──────────────────────────────────────────────────────────────────────────────
# Тексты
# ──────────────────────────────────────────────────────────────────────────────
T_GREETING = (
    "Здравствуй, товарищ! 🥃\n"
    "Я Евгенич — помогу забронировать столик за минуту.\n\n"
    "Выбирай заведение:"
)
T_ASK_DATE   = "📅 На какую дату? (например: 25.04 или «сегодня», «завтра»)"
T_ASK_TIME   = "🕐 На какое время? (например: 19:30)"
T_ASK_GUESTS = "👥 Сколько будет гостей? (число от 1 до 20)"
T_ASK_NAME   = "👤 Как тебя зовут? Напиши имя, чтобы менеджер обратился по-человечески."
T_ASK_PHONE  = "📞 Контактный телефон? Формата +7 (___) ___-__-__ или просто цифрами."
T_CONFIRM_TPL = (
    "Проверяй, всё верно?\n\n"
    "📍 {bar}\n"
    "📅 {date}\n"
    "🕐 {time}\n"
    "👥 {guests} гост(я/ей)\n"
    "👤 {name}\n"
    "📞 {phone}\n\n"
    "Напиши «Да» — отправлю менеджеру. «Нет» — отменим и начнём заново."
)
T_DONE = (
    "Готово, товарищ! ✅\n"
    "Бронь передал менеджеру. С тобой свяжутся в ближайшее время для подтверждения.\n\n"
    "До встречи в Евгениче! 🥃"
)
T_CANCELLED = "Отменил. Если захочешь начать заново — просто напиши «бронь» или «столик»."
T_BAD_DATE   = "Хм, не понял дату. Напиши в формате 25.04 или 25.04.2026 (либо «сегодня», «завтра»)."
T_BAD_TIME   = "Не разобрал время. Напиши в формате 19:30 (часы:минуты)."
T_BAD_GUESTS = "Нужно число от 1 до 20. Сколько гостей?"
T_BAD_PHONE  = "Похоже, телефон не полный. Нужно минимум 10 цифр, например +7 999 123-45-67."
T_BAD_BAR    = "Выбери одно из заведений кнопкой ниже:"
T_FALLBACK   = (
    "Здорово, товарищ! 🥃\n"
    "Я Евгенич — за стойкой и всегда на связи. Могу забронировать столик, "
    "рассказать про бары на Пятницкой и Цветном или позвать старшего, "
    "если вопрос совсем уж непростой.\n\n"
    "С чем помочь?"
)
T_AI_FOOTER = (
    "\n\nЕсли захочешь забронировать столик — жми кнопку ниже. "
    "Если нужен живой человек — позову старшего."
)
T_MANAGER_CALLED = (
    "Передал твоё сообщение старшему 🙋\n"
    "С тобой свяжутся в ближайшее время."
)
T_USE_SAVED_CONTACT = (
    "Помню тебя, товарищ! 🙌\n"
    "В прошлый раз бронировали на:\n"
    "👤 {name}\n📞 {phone}\n\n"
    "Использовать те же контакты или ввести новые?"
)

# ──────────────────────────────────────────────────────────────────────────────
# Клавиатуры VK
# ──────────────────────────────────────────────────────────────────────────────
def _kb_bars() -> str:
    """Inline-клавиатура VK с выбором бара."""
    return json.dumps({
        "one_time": False,
        "inline": False,
        "buttons": [
            [{
                "action": {"type": "text", "label": b["label"], "payload": json.dumps({"bar": b["key"]})},
                "color": "primary",
            }]
            for b in BARS
        ] + [[{
            "action": {"type": "text", "label": "❌ Отмена", "payload": json.dumps({"cancel": True})},
            "color": "negative",
        }]],
    }, ensure_ascii=False)

def _kb_confirm() -> str:
    return json.dumps({
        "one_time": True,
        "inline": False,
        "buttons": [
            [{"action": {"type": "text", "label": "✅ Да, отправляем"}, "color": "positive"}],
            [{"action": {"type": "text", "label": "❌ Отмена"},          "color": "negative"}],
        ],
    }, ensure_ascii=False)

def _kb_cancel() -> str:
    return json.dumps({
        "one_time": False,
        "inline": False,
        "buttons": [[{"action": {"type": "text", "label": "❌ Отмена"}, "color": "negative"}]],
    }, ensure_ascii=False)

def _kb_empty() -> str:
    return json.dumps({"buttons": [], "one_time": True}, ensure_ascii=False)

def _kb_use_saved_contact() -> str:
    """Кнопки на шаге name: использовать сохранённый контакт или ввести новый."""
    return json.dumps({
        "one_time": True,
        "inline": False,
        "buttons": [
            [{
                "action": {"type": "text", "label": "✅ Да, эти данные",
                           "payload": json.dumps({"use_saved": True})},
                "color": "positive",
            }],
            [{
                "action": {"type": "text", "label": "✏️ Ввести новые",
                           "payload": json.dumps({"new_contact": True})},
                "color": "secondary",
            }],
            [{"action": {"type": "text", "label": "❌ Отмена"}, "color": "negative"}],
        ],
    }, ensure_ascii=False)

def _kb_smalltalk() -> str:
    """Клавиатура после AI-ответа: предложить бронь или вызвать менеджера."""
    return json.dumps({
        "one_time": False,
        "inline": False,
        "buttons": [
            [{
                "action": {"type": "text", "label": "🎫 Забронировать столик",
                           "payload": json.dumps({"start_booking": True})},
                "color": "primary",
            }],
            [{
                "action": {"type": "text", "label": "🙋 Позвать старшего",
                           "payload": json.dumps({"call_manager": True})},
                "color": "secondary",
            }],
        ],
    }, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────────────
# VK API helpers
# ──────────────────────────────────────────────────────────────────────────────
_VK_API = "https://api.vk.com/method"
_VK_VERSION = "5.199"

def _vk_send(user_id: int, text: str, keyboard: Optional[str] = None) -> None:
    """Отправляет сообщение пользователю VK. Глотает любые ошибки сети с логом."""
    if not VK_GROUP_TOKEN:
        logger.warning("VK_GROUP_TOKEN не задан — сообщение пользователю %s не отправлено", user_id)
        return
    payload = {
        "access_token": VK_GROUP_TOKEN,
        "v": _VK_VERSION,
        "user_id": user_id,
        "message": text,
        "random_id": int(time.time() * 1000) ^ user_id,  # уникальность в рамках пользователя
        "dont_parse_links": 0,
    }
    if keyboard is not None:
        payload["keyboard"] = keyboard
    try:
        r = requests.post(f"{_VK_API}/messages.send", data=payload, timeout=10)
        data = r.json()
        if "error" in data:
            logger.error("VK messages.send error для %s: %s", user_id, data["error"])
    except Exception as e:
        logger.exception("VK messages.send упал для %s: %s", user_id, e)


def _tg_notify(text: str) -> None:
    """Шлёт уведомление в Telegram-чат менеджеров (МСК-чат броней)."""
    chat_id = BOOKING_NOTIFICATIONS_CHAT_ID_MSK or REPORT_CHAT_ID
    if not BOT_TOKEN or not chat_id:
        logger.warning("BOT_TOKEN/чат уведомлений не настроены — Telegram-уведомление пропущено")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        if not r.ok:
            logger.error("Telegram sendMessage не ок: %s %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.exception("Telegram уведомление упало: %s", e)


# ──────────────────────────────────────────────────────────────────────────────
# Google Sheets экспорт (аналогично TG-броням, gid=1842872487)
# ──────────────────────────────────────────────────────────────────────────────
_SHEETS_GID = "1842872487"  # вкладка "Заявки из Соц сетей" (та же, что у TG-броней)

def _clean_phone_for_sheets(phone: str) -> str:
    """+7… → 7…, чтобы Sheets не превращал в формулу/число."""
    return re.sub(r"\D+", "", phone or "")

def _moscow_now_str() -> str:
    """Текущее время по МСК (UTC+3) в формате '%d.%m.%Y %H:%M'."""
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M")

def _export_vk_to_sheets(s: dict, vk_user_id: int, vk_profile: Optional[dict]) -> bool:
    """Пишет VK-бронь в основную Google-таблицу (вкладка 'Заявки из Соц сетей').
    Колонки и UTM — как у гостевых TG-броней, отличается:
      G (ТЕГ для АМО) = код бара (ЕВГ_МСК_ПЯТ / ЕВГ_МСК_ЦВЕТ)
      F (Источник) = "🟦 Гостевое бронирование (ВК)"
      J (UTM Source) = "vk"
      H (Кто создал) = "👤 Посетитель (через ВК)"
    """
    raw_creds = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
    sheet_key = os.getenv("GOOGLE_SHEET_KEY", "")
    if not raw_creds or not sheet_key:
        logger.info("VK→Sheets: GOOGLE_SHEET_KEY/GOOGLE_CREDENTIALS_JSON не заданы — пропускаю экспорт")
        return False
    try:
        import gspread  # лениво, чтобы импорт не падал при отсутствии пакета
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        logger.error("VK→Sheets: gspread/google-auth не установлены: %s", e)
        return False

    # Парсим credentials (поддерживаем и dict, и многострочный JSON)
    try:
        creds_info = json.loads(raw_creds)
    except (ValueError, TypeError):
        try:
            cleaned = " ".join(line.strip() for line in raw_creds.split("\n") if line.strip())
            creds_info = json.loads(cleaned)
        except Exception as e:
            logger.error("VK→Sheets: не удалось распарсить GOOGLE_CREDENTIALS_JSON: %s", e)
            return False

    try:
        creds = Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(sheet_key)
        worksheet = None
        for ws in sheet.worksheets():
            if str(ws.id) == _SHEETS_GID:
                worksheet = ws
                break
        if not worksheet:
            logger.error("VK→Sheets: вкладка gid=%s не найдена", _SHEETS_GID)
            return False

        bar_info = _BAR_BY_KEY.get(s.get("bar_key"), {})
        amo_tag = bar_info.get("code", "VK_GUEST")
        datetime_combined = f"{s.get('date','')} {s.get('time','')}".strip()
        profile_name = ""
        if vk_profile:
            profile_name = f"{vk_profile.get('first_name','')} {vk_profile.get('last_name','')}".strip()

        row = [
            _moscow_now_str(),                                  # A: Дата заявки
            s.get("name", ""),                                  # B: Имя гостя
            _clean_phone_for_sheets(s.get("phone", "")),        # C: Телефон
            datetime_combined,                                  # D: Дата и время посещения
            s.get("guests", ""),                                # E: Кол-во гостей
            "🟦 Гостевое бронирование (ВК)",                    # F: Источник
            amo_tag,                                            # G: ТЕГ для АМО (код бара)
            "👤 Посетитель (через ВК)",                          # H: Кто создал
            "Новая",                                            # I: Статус
            "vk",                                               # J: UTM Source
            "social",                                           # K: UTM Medium
            "guest_booking",                                    # L: UTM Campaign
            "vk_bot_guest_booking",                             # M: UTM Content
            "guest_vk",                                         # N: UTM Term
            f"VK-{int(time.time())}",                           # O: ID заявки
            f"vk:{vk_user_id}{(' (' + profile_name + ')') if profile_name else ''}",  # P: VK ID создателя
        ]
        worksheet.append_row(row)
        logger.info("VK→Sheets: бронь добавлена. user=%s bar=%s", vk_user_id, amo_tag)
        return True
    except Exception as e:
        logger.exception("VK→Sheets: ошибка экспорта: %s", e)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# AI-ассистент (свободные вопросы, не сценарий брони)
# ──────────────────────────────────────────────────────────────────────────────
_AI_SYSTEM_BASE = (
    "Ты Евгенич — бот-бармен сети рюмочных «Евгенич». "
    "Города: Москва (Пятницкая 30 и Цветной бульвар) и Санкт-Петербург. "
    "В ВКонтакте принимаем брони только по Москве. "
    "Часы работы: каждый день с 12:00 до 02:00, пт-сб до 04:00. "
    "Специализация — авторские настойки и закуски в советском стиле.\n\n"
    "Стиль общения:\n"
    "— на «ты», по-дружески, как с приятелем у барной стойки\n"
    "— коротко: 2–4 предложения, не лекция\n"
    "— не больше одного эмодзи на сообщение\n"
    "— иногда задавай встречный вопрос, чтобы разговор шёл живее\n"
    "— используй обращения «товарищ», «дружище» — но в меру\n\n"
    "Правила:\n"
    "— НЕ выдумывай меню, конкретные цены, акции и наличие — если не уверен, направь к старшему\n"
    "— если гость хочет забронировать — скажи коротко «сейчас оформим, выбери бар» (кнопки сам покажу)\n"
    "— если вопрос совсем не по теме бара — мягко предложи позвать старшего\n"
    "— помни предыдущие реплики гостя в этом диалоге"
)

def _build_ai_messages(user_text: str, vk_user_id: int,
                       vk_profile: Optional[dict]) -> list:
    """Собирает messages для OpenAI: system + история + текущая реплика."""
    system = _AI_SYSTEM_BASE
    if vk_profile and vk_profile.get("first_name"):
        system += f"\n\nГостя зовут {vk_profile['first_name']} — обращайся по имени, когда уместно."
    saved = _get_saved_contact(vk_user_id)
    if saved:
        system += (
            f"\n\nВажно: гость уже бронировал у нас (на имя {saved.get('name','?')}). "
            f"Если попросит — можешь упомянуть, что помнишь его и контакты на месте."
        )

    messages = [{"role": "system", "content": system}]
    history = _get_chat_history(vk_user_id)
    for h in history[-_CHAT_HISTORY_MAX * 2:]:
        role = h.get("role")
        content = h.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text[:1000]})
    return messages

def _ai_reply(user_text: str, vk_user_id: int,
              vk_profile: Optional[dict] = None) -> Optional[str]:
    """Спрашиваем OpenAI с учётом истории диалога. None при любой ошибке."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # lazy import
    except ImportError:
        logger.warning("VK AI: пакет openai не установлен")
        return None
    try:
        client = OpenAI(api_key=api_key, timeout=12.0)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=_build_ai_messages(user_text, vk_user_id, vk_profile),
            temperature=0.7,
            max_tokens=220,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            _append_chat_history(vk_user_id, "user", user_text)
            _append_chat_history(vk_user_id, "assistant", text)
        return text or None
    except Exception as e:
        logger.warning("VK AI: ошибка OpenAI: %s", e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Сессия пользователя (TinyDB)
# ──────────────────────────────────────────────────────────────────────────────
def _get_session(vk_user_id: int) -> Optional[dict]:
    with _db_lock:
        rows = _db.search(_Session.vk_user_id == vk_user_id)
        return rows[0] if rows else None

def _save_session(vk_user_id: int, data: dict) -> None:
    data["vk_user_id"] = vk_user_id
    data["updated_at"] = datetime.utcnow().isoformat()
    with _db_lock:
        _db.upsert(data, _Session.vk_user_id == vk_user_id)

def _drop_session(vk_user_id: int) -> None:
    with _db_lock:
        _db.remove(_Session.vk_user_id == vk_user_id)


# ──────────────────────────────────────────────────────────────────────────────
# Память контактов гостя (имя/телефон) — между бронями
# ──────────────────────────────────────────────────────────────────────────────
def _get_saved_contact(vk_user_id: int) -> Optional[dict]:
    with _db_lock:
        rows = _contacts_table.search(_Contact.vk_user_id == vk_user_id)
        return rows[0] if rows else None

def _save_contact(vk_user_id: int, name: str, phone: str) -> None:
    with _db_lock:
        _contacts_table.upsert(
            {"vk_user_id": vk_user_id, "name": name, "phone": phone,
             "updated_at": datetime.utcnow().isoformat()},
            _Contact.vk_user_id == vk_user_id,
        )


# ──────────────────────────────────────────────────────────────────────────────
# История диалога для AI (последние 10 пар user/assistant) — в той же сессии
# ──────────────────────────────────────────────────────────────────────────────
_CHAT_HISTORY_MAX = 10

def _get_chat_history(vk_user_id: int) -> list:
    with _db_lock:
        rows = _db.search(_Session.vk_user_id == vk_user_id)
        if rows:
            return rows[0].get("chat_history", []) or []
    return []

def _append_chat_history(vk_user_id: int, role: str, content: str) -> None:
    """Хранит историю в той же записи сессии (или создаёт новую запись без 'step')."""
    with _db_lock:
        rows = _db.search(_Session.vk_user_id == vk_user_id)
        history = rows[0].get("chat_history", []) if rows else []
        history.append({"role": role, "content": content[:500]})
        history = history[-_CHAT_HISTORY_MAX * 2:]  # пары user/assistant
        if rows:
            _db.update({"chat_history": history,
                        "updated_at": datetime.utcnow().isoformat()},
                       _Session.vk_user_id == vk_user_id)
        else:
            _db.insert({"vk_user_id": vk_user_id,
                        "chat_history": history,
                        "updated_at": datetime.utcnow().isoformat()})


# ──────────────────────────────────────────────────────────────────────────────
# Парсеры пользовательского ввода
# ──────────────────────────────────────────────────────────────────────────────
_DATE_RE = re.compile(r"^(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?$")
_TIME_RE = re.compile(r"^(\d{1,2})[:.\- ](\d{2})$")
_PHONE_DIGITS_RE = re.compile(r"\D+")
_BOOKING_TRIGGERS = (
    "бронь", "брон", "столик", "стол ", "забронир", "резерв",
    "book", "booking", "забронировать", "/book", "/start",
)

def _parse_date(text: str) -> Optional[str]:
    t = text.strip().lower()
    today = datetime.now()
    if t in ("сегодня", "сегодн", "today"):
        return today.strftime("%d.%m.%Y")
    if t in ("завтра", "завтр", "tomorrow"):
        return (today + timedelta(days=1)).strftime("%d.%m.%Y")
    m = _DATE_RE.match(t)
    if not m:
        return None
    d, mn, y = m.group(1), m.group(2), m.group(3)
    try:
        day, month = int(d), int(mn)
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return None
        if y:
            year = int(y)
            if year < 100:
                year += 2000
        else:
            year = today.year
            # если дата уже прошла в этом году — берём следующий
            try:
                if datetime(year, month, day).date() < today.date():
                    year += 1
            except ValueError:
                return None
        return f"{day:02d}.{month:02d}.{year}"
    except ValueError:
        return None

def _parse_time(text: str) -> Optional[str]:
    m = _TIME_RE.match(text.strip())
    if not m:
        return None
    h, mn = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mn <= 59):
        return None
    return f"{h:02d}:{mn:02d}"

def _parse_guests(text: str) -> Optional[int]:
    digits = _PHONE_DIGITS_RE.sub("", text.strip())
    if not digits:
        return None
    try:
        n = int(digits)
        return n if 1 <= n <= 20 else None
    except ValueError:
        return None

def _parse_phone(text: str) -> Optional[str]:
    raw = text.strip()
    digits = _PHONE_DIGITS_RE.sub("", raw)
    if len(digits) < 10:
        return None
    # Нормализуем к +7XXXXXXXXXX
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return "+" + digits  # если уже с другим кодом страны


def _is_booking_trigger(text: str) -> bool:
    t = text.lower().strip()
    return any(trig in t for trig in _BOOKING_TRIGGERS)

def _is_cancel(text: str) -> bool:
    return text.strip().lower() in ("отмена", "❌ отмена", "cancel", "/cancel", "стоп", "нет")

def _is_yes(text: str) -> bool:
    t = text.strip().lower()
    return t in ("да", "✅ да, отправляем", "ok", "ок", "yes", "+", "подтверждаю")


# ──────────────────────────────────────────────────────────────────────────────
# Шаги сценария
# ──────────────────────────────────────────────────────────────────────────────
def _start_flow(vk_user_id: int) -> None:
    _save_session(vk_user_id, {"step": "bar"})
    _vk_send(vk_user_id, T_GREETING, _kb_bars())

def _ask_date(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_DATE, _kb_cancel())

def _ask_time(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_TIME, _kb_cancel())

def _ask_guests(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_GUESTS, _kb_cancel())

def _ask_name(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_NAME, _kb_cancel())

def _ask_phone(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_PHONE, _kb_cancel())

def _ask_confirm(vk_user_id: int, s: dict) -> None:
    bar = _BAR_BY_KEY.get(s.get("bar_key"), {}).get("name", "—")
    text = T_CONFIRM_TPL.format(
        bar=bar, date=s.get("date", "—"), time=s.get("time", "—"),
        guests=s.get("guests", "—"), name=s.get("name", "—"), phone=s.get("phone", "—"),
    )
    _vk_send(vk_user_id, text, _kb_confirm())


def _finalize(vk_user_id: int, s: dict, vk_profile: Optional[dict]) -> None:
    """Подтверждение → уведомление в Telegram-чат менеджеров + завершение."""
    bar_info = _BAR_BY_KEY.get(s.get("bar_key"), {})
    vk_link = f"https://vk.com/id{vk_user_id}"
    profile_name = ""
    if vk_profile:
        profile_name = f"{vk_profile.get('first_name','')} {vk_profile.get('last_name','')}".strip()

    msg = (
        "🆕 <b>НОВАЯ БРОНЬ из ВКонтакте</b>\n\n"
        f"📍 <b>{bar_info.get('name', '—')}</b> ({bar_info.get('code', '')})\n"
        f"📅 Дата: <b>{s.get('date', '—')}</b>\n"
        f"🕐 Время: <b>{s.get('time', '—')}</b>\n"
        f"👥 Гостей: <b>{s.get('guests', '—')}</b>\n\n"
        f"👤 Имя: <b>{s.get('name', '—')}</b>\n"
        f"📞 Телефон: <b>{s.get('phone', '—')}</b>\n\n"
        f"🔗 VK-профиль: <a href=\"{vk_link}\">{profile_name or vk_link}</a>\n"
        f"🆔 VK ID: <code>{vk_user_id}</code>\n"
        f"🌐 Источник: <b>VK сообщество</b>"
    )
    _tg_notify(msg)
    # Экспорт в Google Sheets — best-effort, не блокирует ответ гостю
    try:
        _export_vk_to_sheets(s, vk_user_id, vk_profile)
    except Exception as e:
        logger.exception("VK→Sheets вызов упал: %s", e)
    _vk_send(vk_user_id, T_DONE, _kb_empty())
    _drop_session(vk_user_id)
    logger.info("VK booking confirmed: vk_user=%s bar=%s date=%s time=%s",
                vk_user_id, bar_info.get("code"), s.get("date"), s.get("time"))


# ──────────────────────────────────────────────────────────────────────────────
# Главный обработчик входящего сообщения от VK
# ──────────────────────────────────────────────────────────────────────────────
def handle_message(vk_user_id: int, text: str, payload: Optional[dict] = None,
                   vk_profile: Optional[dict] = None) -> None:
    """Роутер шагов. Не бросает исключения наружу.
    Защищён per-user lock — два одновременных события одного пользователя
    обрабатываются последовательно, без race condition на TinyDB-сессии.
    """
    text = (text or "").strip()
    lock = _get_user_lock(vk_user_id)
    with lock:
        try:
            # Глобальная отмена
            if _is_cancel(text) or (payload and payload.get("cancel")):
                if _get_session(vk_user_id):
                    _drop_session(vk_user_id)
                    _vk_send(vk_user_id, T_CANCELLED, _kb_empty())
                else:
                    _vk_send(vk_user_id, T_FALLBACK, _kb_empty())
                return

            s = _get_session(vk_user_id)

            # Нет активной сессии → стартуем по триггеру/кнопке или подключаем AI
            if not s:
                # Кнопка «🎫 Забронировать столик» из smalltalk-клавиатуры
                if payload and payload.get("start_booking"):
                    _start_flow(vk_user_id)
                    return

                # Кнопка «🙋 Позвать старшего» — уведомление в TG-чат менеджеров
                if payload and payload.get("call_manager"):
                    profile_name = ""
                    if vk_profile:
                        profile_name = f"{vk_profile.get('first_name','')} {vk_profile.get('last_name','')}".strip()
                    vk_link = f"https://vk.com/id{vk_user_id}"
                    _tg_notify(
                        "🙋 <b>Гость из ВКонтакте просит старшего</b>\n\n"
                        f"👤 {profile_name or '—'}\n"
                        f"🔗 <a href=\"{vk_link}\">{vk_link}</a>\n"
                        f"🆔 VK ID: <code>{vk_user_id}</code>\n\n"
                        "Свяжитесь с гостем напрямую."
                    )
                    _vk_send(vk_user_id, T_MANAGER_CALLED, _kb_empty())
                    return

                # Триггер брони — стартуем сценарий
                if _is_booking_trigger(text) or (payload and payload.get("bar")):
                    _start_flow(vk_user_id)
                    if payload and payload.get("bar"):
                        s = _get_session(vk_user_id)
                    else:
                        return
                else:
                    # Свободный вопрос → пробуем AI
                    if text:
                        ai_text = _ai_reply(text)
                        if ai_text:
                            _vk_send(vk_user_id, ai_text + T_AI_FOOTER, _kb_smalltalk())
                            return
                    # AI выключен/упал/пустой текст — старый фоллбэк
                    _vk_send(vk_user_id, T_FALLBACK, _kb_smalltalk())
                    return

            step = s.get("step", "bar")

            # ── ШАГ: bar ─────────────────────────────────
            if step == "bar":
                bar_key = None
                if payload and payload.get("bar"):
                    bar_key = payload["bar"]
                else:
                    low = text.lower()
                    if low in _BAR_BY_LABEL:
                        bar_key = _BAR_BY_LABEL[low]["key"]
                    elif "пятниц" in low:
                        bar_key = "pyatnitskaya"
                    elif "цветн" in low:
                        bar_key = "tsvetnoj"
                if not bar_key or bar_key not in _BAR_BY_KEY:
                    _vk_send(vk_user_id, T_BAD_BAR, _kb_bars())
                    return
                s["bar_key"] = bar_key
                s["step"] = "date"
                _save_session(vk_user_id, s)
                _ask_date(vk_user_id)
                return

            # ── ШАГ: date ────────────────────────────────
            if step == "date":
                date = _parse_date(text)
                if not date:
                    _vk_send(vk_user_id, T_BAD_DATE, _kb_cancel())
                    return
                s["date"] = date
                s["step"] = "time"
                _save_session(vk_user_id, s)
                _ask_time(vk_user_id)
                return

            # ── ШАГ: time ────────────────────────────────
            if step == "time":
                t = _parse_time(text)
                if not t:
                    _vk_send(vk_user_id, T_BAD_TIME, _kb_cancel())
                    return
                s["time"] = t
                s["step"] = "guests"
                _save_session(vk_user_id, s)
                _ask_guests(vk_user_id)
                return

            # ── ШАГ: guests ──────────────────────────────
            if step == "guests":
                n = _parse_guests(text)
                if not n:
                    _vk_send(vk_user_id, T_BAD_GUESTS, _kb_cancel())
                    return
                s["guests"] = n
                s["step"] = "name"
                _save_session(vk_user_id, s)
                _ask_name(vk_user_id)
                return

            # ── ШАГ: name ────────────────────────────────
            if step == "name":
                name = text.strip()
                if len(name) < 2:
                    _vk_send(vk_user_id, "Имя слишком короткое. Напиши, как обращаться.", _kb_cancel())
                    return
                s["name"] = name[:60]
                s["step"] = "phone"
                _save_session(vk_user_id, s)
                _ask_phone(vk_user_id)
                return

            # ── ШАГ: phone ───────────────────────────────
            if step == "phone":
                phone = _parse_phone(text)
                if not phone:
                    _vk_send(vk_user_id, T_BAD_PHONE, _kb_cancel())
                    return
                s["phone"] = phone
                s["step"] = "confirm"
                _save_session(vk_user_id, s)
                _ask_confirm(vk_user_id, s)
                return

            # ── ШАГ: confirm ─────────────────────────────
            if step == "confirm":
                if _is_yes(text):
                    _finalize(vk_user_id, s, vk_profile)
                else:
                    # Что угодно кроме «да» считаем уточнением → переспросим
                    _vk_send(
                        vk_user_id,
                        'Если что-то не так — напиши «отмена» и начнём заново. '
                        'Если всё ок — нажми «✅ Да, отправляем».',
                        _kb_confirm(),
                    )
                return

            # Неизвестный шаг → сбрасываем
            logger.warning("VK: неизвестный шаг %s у vk_user=%s — сброс сессии", step, vk_user_id)
            _drop_session(vk_user_id)
            _vk_send(vk_user_id, T_FALLBACK, _kb_empty())

        except Exception as e:
            logger.exception("VK handle_message упал для vk_user=%s: %s", vk_user_id, e)
            try:
                _vk_send(vk_user_id, "Что-то пошло не так с моей стороны 🙁 Напиши «бронь» — начнём заново.", _kb_empty())
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Точка входа из web/app.py — обработка Callback API event
# ──────────────────────────────────────────────────────────────────────────────
def process_callback_event(event: dict) -> str:
    """
    Обрабатывает payload Callback API VK.
    Возвращает строку, которую нужно отдать ВК (для confirmation — токен, иначе 'ok').
    """
    if not VK_ENABLED:
        return "ok"

    etype = event.get("type")

    # 1. Подтверждение сервера при настройке Callback API
    if etype == "confirmation":
        return VK_CONFIRMATION_TOKEN or "ok"

    # 2. Дедупликация: VK повторяет события если не получил 'ok' за 10 сек.
    # event_id одинаковый у повторов — игнорируем уже обработанные.
    event_id = event.get("event_id")
    if _is_duplicate_event(event_id):
        logger.info("VK: дубль event_id=%s — пропускаем", event_id)
        return "ok"

    # 3. Новое сообщение — обрабатываем В ФОНЕ, чтобы вернуть 'ok' мгновенно.
    # Иначе VK может не дождаться ответа за 10 сек (особенно если VK API или
    # Telegram API подвисает) и повторит событие → race condition в state machine.
    if etype == "message_new":
        obj = event.get("object", {}) or {}
        msg = obj.get("message", obj)
        vk_user_id = msg.get("from_id")
        if not vk_user_id or vk_user_id < 0:
            return "ok"
        text = msg.get("text", "") or ""
        payload_raw = msg.get("payload")
        payload = None
        if payload_raw:
            try:
                payload = json.loads(payload_raw)
            except (ValueError, TypeError):
                payload = None
        profiles = obj.get("client_info", {}).get("profiles") if isinstance(obj.get("client_info"), dict) else None
        vk_profile = profiles[0] if profiles else None

        # Фоновый поток — не блокируем ответ VK
        threading.Thread(
            target=handle_message,
            args=(vk_user_id, text, payload, vk_profile),
            daemon=True,
            name=f"vk-handler-{vk_user_id}",
        ).start()
        return "ok"

    # Любые другие события игнорируем
    logger.debug("VK: пропущено событие типа %s", etype)
    return "ok"


def verify_secret(provided_secret: Optional[str]) -> bool:
    """True, если переданный секрет валиден ИЛИ если секрет не задан (тогда не проверяем)."""
    if not VK_SECRET_KEY:
        return True
    return provided_secret == VK_SECRET_KEY
