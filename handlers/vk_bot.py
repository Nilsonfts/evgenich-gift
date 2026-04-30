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
    "Я понимаю только сценарий бронирования столика 🥃\n"
    'Напиши «бронь» или «столик» — забронируем за минуту.'
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
    _vk_send(vk_user_id, T_DONE, _kb_empty())
    _drop_session(vk_user_id)
    logger.info("VK booking confirmed: vk_user=%s bar=%s date=%s time=%s",
                vk_user_id, bar_info.get("code"), s.get("date"), s.get("time"))


# ──────────────────────────────────────────────────────────────────────────────
# Главный обработчик входящего сообщения от VK
# ──────────────────────────────────────────────────────────────────────────────
def handle_message(vk_user_id: int, text: str, payload: Optional[dict] = None,
                   vk_profile: Optional[dict] = None) -> None:
    """Роутер шагов. Не бросает исключения наружу."""
    text = (text or "").strip()
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

        # Нет активной сессии → стартуем по триггеру или показываем приглашение
        if not s:
            if _is_booking_trigger(text) or (payload and payload.get("bar")):
                _start_flow(vk_user_id)
                # Если в payload уже есть bar — сразу обработаем как ответ на шаге bar
                if payload and payload.get("bar"):
                    s = _get_session(vk_user_id)  # перечитываем
                else:
                    return
            else:
                _vk_send(vk_user_id, T_FALLBACK, _kb_empty())
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

    # 2. Новое сообщение
    if etype == "message_new":
        obj = event.get("object", {}) or {}
        msg = obj.get("message", obj)  # в новых версиях message вложен, в старых — на уровне object
        vk_user_id = msg.get("from_id")
        if not vk_user_id or vk_user_id < 0:
            # Группа писать сама себе не должна; отбрасываем
            return "ok"
        text = msg.get("text", "") or ""
        payload_raw = msg.get("payload")
        payload = None
        if payload_raw:
            try:
                payload = json.loads(payload_raw)
            except (ValueError, TypeError):
                payload = None

        # client_info / профиль — берём из вложенного profiles, если есть
        profiles = obj.get("client_info", {}).get("profiles") if isinstance(obj.get("client_info"), dict) else None
        vk_profile = profiles[0] if profiles else None

        handle_message(vk_user_id, text, payload=payload, vk_profile=vk_profile)
        return "ok"

    # Любые другие события игнорируем (можно расширять при необходимости)
    logger.debug("VK: пропущено событие типа %s", etype)
    return "ok"


def verify_secret(provided_secret: Optional[str]) -> bool:
    """True, если переданный секрет валиден ИЛИ если секрет не задан (тогда не проверяем)."""
    if not VK_SECRET_KEY:
        return True
    return provided_secret == VK_SECRET_KEY
