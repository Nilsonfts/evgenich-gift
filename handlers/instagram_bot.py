# /handlers/instagram_bot.py
"""
Instagram Direct AI-бот «Евгенич МСК».

Принимает входящие сообщения от Meta Graph API (через web/app.py:/instagram/webhook),
ведёт сценарий бронирования (телефон → имя → дата → время → гости → бар → подтверждение),
а на свободные вопросы отвечает через AI с базой знаний по МСК-барам.

Бары: только Москва — Пятницкая 30с1 и Цветной бульвар 11с3.
В n8n-вебхук уходит source=smm, medium=instagram.

Переиспользует из vk_bot: парсеры даты/времени/телефона, AI-ассистент,
базу знаний, варианты приветствий и финалок, TG-уведомление менеджерам.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import requests
from tinydb import Query, TinyDB

# Переиспользуем всё из VK-бота — парсеры, AI, тексты, базу знаний
from handlers.vk_bot import (
    BARS,
    _BAR_BY_KEY,
    _AI_SYSTEM,
    _BOOKING_MARKER,
    _DONE_VARIANTS,
    _OFFENSIVE_REPLIES,
    _ai_reply,
    _clean_phone_for_sheets,
    _greet_pool_for_hour,
    _GREETINGS_RETURN,
    _GREET_TAIL_NEW,
    _GREET_TAIL_BACK,
    _is_cancel,
    _is_offensive,
    _is_yes,
    _make_done_text,
    _moscow_now,
    _parse_date,
    _parse_guests,
    _parse_phone,
    _parse_time,
    _tg_notify,
    T_ASK_DATE,
    T_ASK_TIME,
    T_ASK_GUESTS,
    T_ASK_NAME,
    T_ASK_PHONE,
    T_ASK_BAR,
    T_BAD_DATE,
    T_BAD_TIME,
    T_BAD_GUESTS,
    T_BAD_PHONE,
    T_CANCELLED,
    T_FALLBACK,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Конфигурация (читается из ENV на каждый вызов — Railway-friendly)
# ──────────────────────────────────────────────────────────────────────────────
def _ig_token() -> str:
    return os.getenv("IG_PAGE_ACCESS_TOKEN", "").strip()


def _ig_verify_token() -> str:
    return os.getenv("IG_VERIFY_TOKEN", "").strip()


def _ig_app_secret() -> str:
    return os.getenv("IG_APP_SECRET", "").strip()


def _ig_business_id() -> str:
    return os.getenv("IG_BUSINESS_ID", "").strip()


def _ig_enabled() -> bool:
    return os.getenv("IG_ENABLED", "1") not in ("", "0", "false", "False")


_GRAPH_API_VERSION = os.getenv("IG_GRAPH_VERSION", "v21.0")
_BOOKING_WEBHOOK_URL = os.getenv("BOOKING_WEBHOOK_URL", "").strip()


# ──────────────────────────────────────────────────────────────────────────────
# Хранилище сессий + контактов гостя (отдельные TinyDB)
# ──────────────────────────────────────────────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(_DATA_DIR, exist_ok=True)

_SESS_DB = TinyDB(os.path.join(_DATA_DIR, "ig_booking_data.json"))
_CONT_DB = TinyDB(os.path.join(_DATA_DIR, "ig_contacts.json"))
_Q = Query()
_db_lock = threading.RLock()

# Per-user lock — два события одного гостя обрабатываются последовательно
_user_locks: dict[str, threading.Lock] = {}
_user_locks_lock = threading.Lock()


def _get_user_lock(ig_user_id: str) -> threading.Lock:
    with _user_locks_lock:
        lock = _user_locks.get(ig_user_id)
        if lock is None:
            lock = threading.Lock()
            _user_locks[ig_user_id] = lock
        return lock


# Дедупликация Meta-событий (mid сообщения)
_seen_mids: list[str] = []
_seen_mids_lock = threading.Lock()
_SEEN_MIDS_MAX = 1000


def _is_duplicate_mid(mid: str) -> bool:
    if not mid:
        return False
    with _seen_mids_lock:
        if mid in _seen_mids:
            return True
        _seen_mids.append(mid)
        if len(_seen_mids) > _SEEN_MIDS_MAX:
            del _seen_mids[: len(_seen_mids) - _SEEN_MIDS_MAX]
        return False


# Idle ping — мягкое напоминание через 2 мин молчания на любом шаге брони
_idle_timers: dict[str, threading.Timer] = {}
_idle_timers_lock = threading.Lock()
_IDLE_PING_DELAY = int(os.getenv("IG_IDLE_PING_SECONDS", "120"))
_IDLE_PING_VARIANTS = [
    "Я тут, не теряйся 🥃 Продолжим бронь?",
    "Эй, товарищ, ты ещё здесь? Допишем бронь?",
    "Не пропадай 😊 Ждём от тебя ответ — и всё закроем.",
]


def _cancel_idle_ping(ig_user_id: str) -> None:
    with _idle_timers_lock:
        t = _idle_timers.pop(ig_user_id, None)
    if t:
        t.cancel()


def _schedule_idle_ping(ig_user_id: str, expected_step: str) -> None:
    _cancel_idle_ping(ig_user_id)

    def _ping():
        try:
            s = _get_session(ig_user_id)
            if not s or s.get("step") != expected_step:
                return
            _ig_send(ig_user_id, random.choice(_IDLE_PING_VARIANTS))
        except Exception as e:
            logger.warning("IG idle ping failed: %s", e)

    timer = threading.Timer(_IDLE_PING_DELAY, _ping)
    timer.daemon = True
    timer.start()
    with _idle_timers_lock:
        _idle_timers[ig_user_id] = timer


# ──────────────────────────────────────────────────────────────────────────────
# Сессии брони
# ──────────────────────────────────────────────────────────────────────────────
def _get_session(ig_user_id: str) -> Optional[dict]:
    with _db_lock:
        rec = _SESS_DB.get(_Q.ig_user_id == ig_user_id)
    return rec or None


def _save_session(ig_user_id: str, data: dict) -> None:
    data["ig_user_id"] = ig_user_id
    data["ts"] = int(time.time())
    with _db_lock:
        if _SESS_DB.contains(_Q.ig_user_id == ig_user_id):
            _SESS_DB.update(data, _Q.ig_user_id == ig_user_id)
        else:
            _SESS_DB.insert(data)


def _drop_session(ig_user_id: str) -> None:
    with _db_lock:
        _SESS_DB.remove(_Q.ig_user_id == ig_user_id)


def _get_contact(ig_user_id: str) -> Optional[dict]:
    with _db_lock:
        rec = _CONT_DB.get(_Q.ig_user_id == ig_user_id)
    return rec or None


def _save_contact(ig_user_id: str, name: str, phone: str) -> None:
    if not (name and phone):
        return
    rec = {"ig_user_id": ig_user_id, "name": name, "phone": phone, "ts": int(time.time())}
    with _db_lock:
        if _CONT_DB.contains(_Q.ig_user_id == ig_user_id):
            _CONT_DB.update(rec, _Q.ig_user_id == ig_user_id)
        else:
            _CONT_DB.insert(rec)


# ──────────────────────────────────────────────────────────────────────────────
# Отправка сообщений в Instagram через Graph API
# ──────────────────────────────────────────────────────────────────────────────
def _ig_send(ig_user_id: str, text: str, quick_replies: Optional[list[str]] = None) -> bool:
    """Отправка direct-сообщения через Graph API.

    Документация: https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message
    """
    token = _ig_token()
    if not token:
        logger.warning("IG_PAGE_ACCESS_TOKEN не задан — сообщение пользователю %s не отправлено", ig_user_id)
        return False
    if not text:
        return False

    url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/me/messages"
    message: dict[str, Any] = {"text": text[:1000]}
    if quick_replies:
        message["quick_replies"] = [
            {"content_type": "text", "title": qr[:20], "payload": qr[:1000]}
            for qr in quick_replies[:13]
        ]
    payload = {
        "recipient": {"id": ig_user_id},
        "message": message,
        "messaging_type": "RESPONSE",
    }
    try:
        r = requests.post(
            url,
            params={"access_token": token},
            json=payload,
            timeout=10,
        )
        if r.status_code >= 400:
            logger.error("IG send failed [%s]: %s", r.status_code, r.text[:500])
            return False
        return True
    except Exception as e:
        logger.exception("IG send exception: %s", e)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# n8n webhook — отправка брони наружу
# ──────────────────────────────────────────────────────────────────────────────
def _send_booking_webhook(ig_user_id: str, s: dict, profile_name: str = "") -> None:
    if not _BOOKING_WEBHOOK_URL:
        return
    bar_info = _BAR_BY_KEY.get(s.get("bar_key"), {})
    payload = {
        "source": "instagram",
        "event": "booking_created",
        "ts": _moscow_now().strftime("%Y-%m-%dT%H:%M:%S+03:00"),
        "booking": {
            "id": f"IG-{int(time.time())}",
            "bar": bar_info.get("name", ""),
            "bar_city": "Москва",
            "amo_tag": bar_info.get("code", ""),
            "date": s.get("date", ""),
            "time": s.get("time", ""),
            "guests": s.get("guests", 0),
            "name": s.get("name", ""),
            "phone": s.get("phone", ""),
            "comment": "",
        },
        "guest": {
            "ig_user_id": ig_user_id,
            "first_name": profile_name or "",
        },
        "utm": {
            "source": "smm",
            "medium": "instagram",
            "campaign": "guest_booking",
            "content": "ig_bot_guest_booking",
            "term": "guest_ig",
        },
        "meta": {"bot": "evgenich-gift", "env": os.getenv("RAILWAY_ENVIRONMENT", "production")},
    }

    def _do():
        try:
            requests.post(_BOOKING_WEBHOOK_URL, json=payload, timeout=5)
        except Exception as e:
            logger.warning("IG booking webhook failed: %s", e)

    threading.Thread(target=_do, daemon=True, name=f"ig-webhook-{ig_user_id}").start()


# ──────────────────────────────────────────────────────────────────────────────
# Sheets — best-effort экспорт (тот же лист, что у TG/VK)
# ──────────────────────────────────────────────────────────────────────────────
_SHEETS_GID = os.getenv("GOOGLE_SHEET_SOCIAL_GID", "1115282124")


def _export_to_sheets(s: dict, ig_user_id: str, profile_name: str = "") -> bool:
    raw_creds = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
    sheet_key = os.getenv("GOOGLE_SHEET_KEY", "")
    if not raw_creds or not sheet_key:
        return False
    try:
        import gspread  # noqa: PLC0415
        from google.oauth2.service_account import Credentials  # noqa: PLC0415
    except ImportError as e:
        logger.error("IG→Sheets: gspread/google-auth не установлены: %s", e)
        return False

    try:
        creds_info = json.loads(raw_creds)
    except (ValueError, TypeError):
        try:
            cleaned = " ".join(line.strip() for line in raw_creds.split("\n") if line.strip())
            creds_info = json.loads(cleaned)
        except Exception as e:
            logger.error("IG→Sheets: bad GOOGLE_CREDENTIALS_JSON: %s", e)
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
            return False

        bar_info = _BAR_BY_KEY.get(s.get("bar_key"), {})
        amo_tag = bar_info.get("code", "IG_GUEST")
        datetime_combined = f"{s.get('date','')} {s.get('time','')}".strip()

        row = [
            _moscow_now().strftime("%d.%m.%Y %H:%M"),       # A
            s.get("name", ""),                               # B
            _clean_phone_for_sheets(s.get("phone", "")),     # C
            datetime_combined,                               # D
            s.get("guests", ""),                             # E
            "🟪 Гостевое бронирование (Instagram)",          # F
            amo_tag,                                          # G
            "👤 Посетитель (через Instagram)",               # H
            "Новая",                                          # I
            "instagram",                                      # J utm_source
            "social",                                         # K utm_medium
            "guest_booking",                                  # L utm_campaign
            "ig_bot_guest_booking",                           # M utm_content
            "guest_ig",                                       # N utm_term
            f"IG-{int(time.time())}",                         # O id
            f"ig:{ig_user_id}{(' (' + profile_name + ')') if profile_name else ''}",  # P
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        logger.exception("IG→Sheets: %s", e)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Тексты подтверждения (своя версия чтобы избежать конфликта импорта)
# ──────────────────────────────────────────────────────────────────────────────
T_CONFIRM_TPL_IG = (
    "Проверяем бронь, товарищ:\n\n"
    "📍 Бар: {bar}\n"
    "📅 Дата: {date}\n"
    "🕐 Время: {time}\n"
    "👥 Гостей: {guests}\n"
    "👤 Имя: {name}\n"
    "📞 Телефон: {phone}\n\n"
    "Всё верно? Ответь «Да» — и я передам менеджеру."
)


# ──────────────────────────────────────────────────────────────────────────────
# Шаги сценария
# ──────────────────────────────────────────────────────────────────────────────
def _make_greeting(ig_user_id: str) -> str:
    hour = _moscow_now().hour
    contact = _get_contact(ig_user_id)
    if contact and contact.get("name"):
        first_name = contact["name"].split()[0]
        head = random.choice(_GREETINGS_RETURN).format(name=first_name)
        tail = _GREET_TAIL_BACK
    else:
        head = random.choice(_greet_pool_for_hour(hour))
        tail = _GREET_TAIL_NEW
    return f"{head}\n{tail}"


def _start_flow(ig_user_id: str) -> None:
    """Стартуем бронь. Если есть сохранённый контакт — пропускаем телефон+имя."""
    contact = _get_contact(ig_user_id)
    if contact and contact.get("phone") and contact.get("name"):
        _save_session(ig_user_id, {
            "step": "date",
            "phone": contact["phone"],
            "name": contact["name"],
        })
        _ig_send(
            ig_user_id,
            f"С возвращением, {contact['name'].split()[0]}! 🥃\n"
            f"Использую твой контакт: {contact['phone']}\n\n{T_ASK_DATE}",
        )
        _schedule_idle_ping(ig_user_id, "date")
    else:
        _save_session(ig_user_id, {"step": "phone"})
        _ig_send(ig_user_id, _make_greeting(ig_user_id) + "\n\n" + T_ASK_PHONE)
        _schedule_idle_ping(ig_user_id, "phone")


def _ask_confirm(ig_user_id: str, s: dict) -> None:
    bar = _BAR_BY_KEY.get(s.get("bar_key"), {}).get("name", "—")
    text = T_CONFIRM_TPL_IG.format(
        bar=bar, date=s.get("date", "—"), time=s.get("time", "—"),
        guests=s.get("guests", "—"), name=s.get("name", "—"), phone=s.get("phone", "—"),
    )
    _ig_send(ig_user_id, text, quick_replies=["✅ Да, отправляем", "❌ Отменить"])


def _finalize(ig_user_id: str, s: dict, profile_name: str = "") -> None:
    bar_info = _BAR_BY_KEY.get(s.get("bar_key"), {})
    msg = (
        "🆕 <b>НОВАЯ БРОНЬ из Instagram</b>\n\n"
        f"📍 <b>{bar_info.get('name', '—')}</b>\n"
        f"🏷 AMO_TAG: <code>{bar_info.get('code', '')}</code>\n"
        f"📅 Дата: <b>{s.get('date', '—')}</b>\n"
        f"🕐 Время: <b>{s.get('time', '—')}</b>\n"
        f"👥 Гостей: <b>{s.get('guests', '—')}</b>\n\n"
        f"👤 Имя: <b>{s.get('name', '—')}</b>\n"
        f"📞 Телефон: <b>{s.get('phone', '—')}</b>\n\n"
        f"📷 Instagram: {profile_name or '—'}\n"
        f"🆔 IG ID: <code>{ig_user_id}</code>\n"
        f"🌐 Источник: <b>Instagram Direct</b>"
    )
    _tg_notify(msg)
    _save_contact(ig_user_id, s.get("name", ""), s.get("phone", ""))
    _export_to_sheets(s, ig_user_id, profile_name)
    _send_booking_webhook(ig_user_id, s, profile_name)
    _drop_session(ig_user_id)
    _cancel_idle_ping(ig_user_id)
    _ig_send(ig_user_id, _make_done_text())


# ──────────────────────────────────────────────────────────────────────────────
# Триггеры
# ──────────────────────────────────────────────────────────────────────────────
_BOOKING_TRIGGERS = (
    "брон", "столик", "стол на", "забронир", "резерв", "хочу прийти", "хочу зайти",
)


def _is_booking_trigger(text: str) -> bool:
    low = (text or "").lower()
    return any(trig in low for trig in _BOOKING_TRIGGERS)


def _match_bar(text: str) -> Optional[dict]:
    low = (text or "").lower()
    if "пятниц" in low or "30" in low:
        return _BAR_BY_KEY.get("pyatnitskaya")
    if "цветн" in low or "11" in low:
        return _BAR_BY_KEY.get("tsvetnoj")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Основной обработчик
# ──────────────────────────────────────────────────────────────────────────────
def handle_message(ig_user_id: str, text: str, attachments: Optional[list] = None,
                   profile_name: str = "") -> None:
    """Основной роутер. Не бросает исключений."""
    text = (text or "").strip()
    lock = _get_user_lock(ig_user_id)
    with lock:
        _cancel_idle_ping(ig_user_id)
        try:
            # Медиа без текста: голосовое → вежливо; фото/видео без текста — молча
            if not text and attachments:
                kinds = {a.get("type") for a in attachments if isinstance(a, dict)}
                if "audio" in kinds:
                    _ig_send(ig_user_id, "Голосовые пока не разбираю 🙏 Напиши текстом — отвечу подробно.")
                    return
                if kinds & {"image", "video", "story_mention", "share", "ig_reel"}:
                    return

            # Глобальная отмена
            if _is_cancel(text):
                if _get_session(ig_user_id):
                    _drop_session(ig_user_id)
                    _cancel_idle_ping(ig_user_id)
                    _ig_send(ig_user_id, T_CANCELLED)
                else:
                    _ig_send(ig_user_id, T_FALLBACK)
                return

            s = _get_session(ig_user_id)

            # Нет активной сессии → AI или старт брони
            if not s:
                # Фильтр мата (только вне сценария)
                if text and _is_offensive(text):
                    _ig_send(ig_user_id, random.choice(_OFFENSIVE_REPLIES))
                    return

                if _is_booking_trigger(text):
                    _start_flow(ig_user_id)
                    return

                if text:
                    ai_text = _ai_reply(text, 0, {"first_name": profile_name} if profile_name else None)
                    if ai_text:
                        if _BOOKING_MARKER in ai_text:
                            clean = ai_text.replace(_BOOKING_MARKER, "").strip()
                            if clean:
                                _ig_send(ig_user_id, clean)
                            _start_flow(ig_user_id)
                            return
                        _ig_send(ig_user_id, ai_text)
                        return
                _ig_send(ig_user_id, T_FALLBACK)
                return

            # ── Шаги сценария ──
            step = s.get("step", "phone")

            if step == "phone":
                phone = _parse_phone(text)
                if not phone:
                    _ig_send(ig_user_id, T_BAD_PHONE)
                    _schedule_idle_ping(ig_user_id, "phone")
                    return
                s["phone"] = phone
                s["step"] = "name"
                _save_session(ig_user_id, s)
                _ig_send(ig_user_id, T_ASK_NAME)
                _schedule_idle_ping(ig_user_id, "name")
                return

            if step == "name":
                if len(text) < 2:
                    _ig_send(ig_user_id, "Имя слишком короткое. Напиши, как к тебе обращаться.")
                    _schedule_idle_ping(ig_user_id, "name")
                    return
                s["name"] = text[:60]
                s["step"] = "date"
                _save_session(ig_user_id, s)
                _ig_send(ig_user_id, T_ASK_DATE)
                _schedule_idle_ping(ig_user_id, "date")
                return

            if step == "date":
                date = _parse_date(text)
                if not date:
                    _ig_send(ig_user_id, T_BAD_DATE)
                    _schedule_idle_ping(ig_user_id, "date")
                    return
                s["date"] = date
                s["step"] = "time"
                _save_session(ig_user_id, s)
                _ig_send(ig_user_id, T_ASK_TIME)
                _schedule_idle_ping(ig_user_id, "time")
                return

            if step == "time":
                t = _parse_time(text)
                if not t:
                    _ig_send(ig_user_id, T_BAD_TIME)
                    _schedule_idle_ping(ig_user_id, "time")
                    return
                s["time"] = t
                s["step"] = "guests"
                _save_session(ig_user_id, s)
                _ig_send(ig_user_id, T_ASK_GUESTS)
                _schedule_idle_ping(ig_user_id, "guests")
                return

            if step == "guests":
                g = _parse_guests(text)
                if not g:
                    _ig_send(ig_user_id, T_BAD_GUESTS)
                    _schedule_idle_ping(ig_user_id, "guests")
                    return
                s["guests"] = g
                s["step"] = "bar"
                _save_session(ig_user_id, s)
                _ig_send(
                    ig_user_id,
                    T_ASK_BAR,
                    quick_replies=["🏛 Пятницкая 30с1", "🌸 Цветной бульвар 11с3"],
                )
                _schedule_idle_ping(ig_user_id, "bar")
                return

            if step == "bar":
                bar = _match_bar(text)
                if not bar:
                    _ig_send(
                        ig_user_id,
                        "Выбери бар кнопкой ниже:",
                        quick_replies=["🏛 Пятницкая 30с1", "🌸 Цветной бульвар 11с3"],
                    )
                    _schedule_idle_ping(ig_user_id, "bar")
                    return
                s["bar_key"] = bar["key"]
                s["step"] = "confirm"
                _save_session(ig_user_id, s)
                _ask_confirm(ig_user_id, s)
                _schedule_idle_ping(ig_user_id, "confirm")
                return

            if step == "confirm":
                if _is_yes(text):
                    _finalize(ig_user_id, s, profile_name)
                else:
                    _ig_send(
                        ig_user_id,
                        "Что-то меняем? Напиши «отмена» — начнём заново, или подтверди «Да».",
                        quick_replies=["✅ Да, отправляем", "❌ Отменить"],
                    )
                    _schedule_idle_ping(ig_user_id, "confirm")
                return

        except Exception as e:
            logger.exception("IG handle_message error: %s", e)


# ──────────────────────────────────────────────────────────────────────────────
# Webhook payload parsing
# ──────────────────────────────────────────────────────────────────────────────
def verify_signature(body_bytes: bytes, signature_header: str) -> bool:
    """Проверка X-Hub-Signature-256 по APP_SECRET."""
    secret = _ig_app_secret()
    if not secret:
        # Если секрет не задан — пропускаем (для удобства начальной настройки)
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, received)


def process_webhook_event(payload: dict) -> None:
    """Парсит входящий JSON от Meta и вызывает handle_message в фоновом потоке.

    Формат: https://developers.facebook.com/docs/messenger-platform/instagram/features/webhook
    {
      "object": "instagram",
      "entry": [{
        "id": "<page_id>",
        "messaging": [{
          "sender": {"id": "<igsid>"},
          "recipient": {"id": "<page_id>"},
          "timestamp": ...,
          "message": {"mid": "...", "text": "...", "attachments": [...]}
        }]
      }]
    }
    """
    if not _ig_enabled():
        return
    if not isinstance(payload, dict):
        return
    if payload.get("object") not in ("instagram", "page"):
        return

    for entry in payload.get("entry", []) or []:
        for ev in entry.get("messaging", []) or []:
            try:
                # Игнорим echo (наши же ответы) и delivery/read
                if ev.get("message", {}).get("is_echo"):
                    continue
                msg = ev.get("message")
                if not msg:
                    continue

                mid = msg.get("mid", "")
                if _is_duplicate_mid(mid):
                    continue

                sender_id = str(ev.get("sender", {}).get("id", ""))
                if not sender_id:
                    continue

                # Quick reply payload идёт в message.quick_reply.payload, фоллбэк — text
                qr_payload = (msg.get("quick_reply") or {}).get("payload", "")
                text = msg.get("text", "") or qr_payload or ""
                attachments = msg.get("attachments") if isinstance(msg.get("attachments"), list) else None

                threading.Thread(
                    target=handle_message,
                    args=(sender_id, text, attachments, ""),
                    daemon=True,
                    name=f"ig-handler-{sender_id}",
                ).start()
            except Exception as e:
                logger.exception("IG event parse error: %s", e)
