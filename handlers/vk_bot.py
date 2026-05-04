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
import random
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
_DATABASE_MODULE = None
_DATABASE_IMPORT_ATTEMPTED = False
_VK_DIALOG_SOURCE = "vk"

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

# Запомненные контакты VK-гостей (имя + телефон последней брони)
_CONTACTS_DB_PATH = os.path.join(
    os.path.dirname(_DB_PATH), "vk_contacts.json"
)
_contacts_db = TinyDB(_CONTACTS_DB_PATH)
_ContactQuery = Query()
_contacts_lock = threading.RLock()


# Межпроцессный файловый лок на сессии — на случай, если gunicorn запущен
# с несколькими worker'ами. TinyDB не безопасен между процессами: при гонке
# один из шагов сценария может быть «потерян» и гость откатится назад.
_FLOCK_PATH = os.path.join(os.path.dirname(_DB_PATH), ".vk_session.lock")
try:
    import fcntl as _fcntl  # POSIX-only, на Railway/Linux всегда есть
except ImportError:  # pragma: no cover
    _fcntl = None  # type: ignore[assignment]


class _CrossProcessLock:
    """Контекст-менеджер: эксклюзивная блокировка файла через fcntl.flock.
    Если fcntl недоступен (Windows) — превращается в no-op.
    """

    def __enter__(self):
        if _fcntl is None:
            return self
        # Открываем (создаём) lock-файл и держим его до выхода из контекста
        self._fh = open(_FLOCK_PATH, "a+")
        try:
            _fcntl.flock(self._fh.fileno(), _fcntl.LOCK_EX)
        except OSError:
            # Если ОС не даёт лок — лучше продолжить, чем уронить запрос
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        if _fcntl is None:
            return False
        try:
            _fcntl.flock(self._fh.fileno(), _fcntl.LOCK_UN)
        finally:
            self._fh.close()
        return False


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
    {"key": "pyatnitskaya", "label": "🏛 Пятницкая 30с1",   "name": "Москва, Пятницкая 30с1",   "code": "ЕВГ_МСК_ПЯТ"},
    {"key": "tsvetnoj",     "label": "🌸 Цветной бульвар 11с3", "name": "Москва, Цветной бульвар 11с3", "code": "ЕВГ_МСК_ЦВЕТ"},
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

# Варианты приветствия — выбираются с учётом времени суток (МСК) и того,
# знаком ли уже гость. Хвост подбирается динамически в зависимости от того,
# с какого шага мы стартуем (нового гостя ведём в имя, повторного — в дату).
_GREET_TAIL_NEW = "Помогу забронировать столик за минуту. Напиши свой номер телефона — от этого пляшем."
_GREET_TAIL_BACK = "Подыщем столик? На какую дату планируем?"

_GREETINGS_MORNING = [
    "Доброе утро, товарищ! ☕",
    "Утро доброе! ☀️ Готовлю стойку.",
    "С добрым утром! 🥃 Уже на смене.",
]
_GREETINGS_DAY = [
    "Здравствуй, товарищ! 🥃",
    "Приветствую! 👋 За стойкой как штык.",
    "Добрый день, товарищ! Чем порадовать?",
    "Здорово, товарищ! 🥃",
    "Ну что, браток, заходи. Чем помочь?",
]
_GREETINGS_EVENING = [
    "Добрый вечер, товарищ! 🌆 Вечер обещает быть ламповым.",
    "Здорово, товарищ! 🥃 Вечер у нас в самом разгаре.",
    "Приветствую! 🍻 К вечеру всё готово.",
    "Ну что, вечер хорош — настойка ждёт. Чем помочь?",
]
_GREETINGS_NIGHT = [
    "Доброй ночи, товарищ! 🌙 Я ещё на посту.",
    "На связи, товарищ. 🥃 Полуночник?",
]

_GREETINGS_RETURN = [
    "С возвращением, {name}! 🥃",
    "О, {name}, рад тебя видеть снова! 👋",
    "Снова на огонёк, {name}? 🔥 Заходи.",
    "Здорово, {name}! Давно не виделись.",
    "{name}, рад снова слышать! 🥃",
]


def _greet_pool_for_hour(hour: int) -> list[str]:
    if 5 <= hour < 11:
        return _GREETINGS_MORNING
    if 11 <= hour < 17:
        return _GREETINGS_DAY
    if 17 <= hour < 23:
        return _GREETINGS_EVENING
    return _GREETINGS_NIGHT


def _make_greeting(vk_user_id: int) -> str:
    """Случайное приветствие с учётом времени суток МСК и знакомства с гостем.

    Если у гостя сохранён контакт (повторное обращение) — приветствуем по имени.
    Иначе — нейтральное приветствие по времени суток. Хвост-инструкция
    про выбор заведения остаётся неизменным.
    """
    hour = _moscow_now().hour
    contact = _get_vk_contact(vk_user_id)
    if contact and contact.get("name"):
        # Возьмём первое имя без отчества/фамилии для естественности
        first_name = contact["name"].split()[0]
        head = random.choice(_GREETINGS_RETURN).format(name=first_name)
        tail = _GREET_TAIL_BACK
    else:
        head = random.choice(_greet_pool_for_hour(hour))
        tail = _GREET_TAIL_NEW
    return f"{head}\n{tail}"
T_ASK_DATE   = "📅 На какую дату? (например: 25.04, «19 мая», «сегодня», «завтра»)"
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

# Варианты финального сообщения после брони. Выбираемся рандомом.
_DONE_VARIANTS = [
    "Готово, товарищ! ✅ Передал бронь менеджеру — созвонятся в ближайшее время.\nЖдём в Евгениче! 🥃",
    "Принял! ✅ Менеджер бара скоро наберёт подтвердить.\nДо встречи! 🥃",
    "Всё, бронь ушла. ✅ Перезвонят для подтверждения — будь на связи.\nЖдём в гости! 🥃",
    "Ровно, товарищ! ✅ Бронь передал, перезвонят подтвердить.\nДо встречи у нас! 🥃",
    "Готово ✅ Менеджер в курсе и скоро свяжется. Отличного вечера!",
    "Ну вот и сговорились. ✅ Бронь у менеджера, перезвонит. Ждём на огонёк! 🥃",
]


def _make_done_text() -> str:
    return random.choice(_DONE_VARIANTS)
T_CANCELLED = "Отменил. Если захочешь начать заново — просто напиши «бронь» или «столик»."
T_BAD_DATE   = "Хм, не понял дату. Напиши в формате 25.04, 25.04.2026, «19 мая» или «сегодня»/«завтра»."
T_BAD_TIME   = "Не разобрал время. Напиши в формате 19:30 (часы:минуты)."
T_BAD_GUESTS = "Нужно число от 1 до 20. Сколько гостей?"
T_BAD_PHONE  = "Похоже, телефон не полный. Нужно минимум 10 цифр, например +7 999 123-45-67."
T_BAD_BAR    = "Выбери одно из заведений кнопкой ниже:"
T_ASK_BAR    = "📍 Отлично! В каком из наших заведений будешь?"
T_RETURNING_CONTACT = (
    "С возвращением, {name}! 🥃\n"
    "Использую твой прошлый контакт: {phone}.\n"
    "Если что-то поменялось — жми «✏️ Изменить контакт»."
)
T_FALLBACK   = (
    "Ну что, товарищ. 🥃\n"
    "Я здесь, за стойкой. Спрашивай по бару: бронь, меню, афиша — подскажу."
)
T_MANAGER_CALLED = (
    "Передал твоё сообщение старшему 🙋\n"
    "С тобой свяжутся в ближайшее время."
)

# ──────────────────────────────────────────────────────────────────────────────
# Расписание старшего (МСК): пн–сб 11:00–22:00, ВС — выходной
# ──────────────────────────────────────────────────────────────────────────────
MANAGER_WORK_START_HOUR = int(os.getenv("VK_MANAGER_START_HOUR", "11"))
MANAGER_WORK_END_HOUR = int(os.getenv("VK_MANAGER_END_HOUR", "22"))
MANAGER_DAY_OFF_WEEKDAY = 6  # Воскресенье (понедельник=0)


def _moscow_now() -> datetime:
    """Текущее время МСК (UTC+3, без DST)."""
    return datetime.utcnow() + timedelta(hours=3)


def _manager_status() -> dict:
    """Возвращает статус старшего на текущий момент в МСК.

    Поля:
        available: bool — старший на смене прямо сейчас
        reason: str — 'on_shift' | 'before_shift' | 'after_shift' | 'day_off'
        next_shift: datetime — когда выйдет на смену (МСК)
    """
    now = _moscow_now()
    weekday = now.weekday()
    today_start = now.replace(hour=MANAGER_WORK_START_HOUR, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=MANAGER_WORK_END_HOUR, minute=0, second=0, microsecond=0)

    # Воскресенье — выходной целиком
    if weekday == MANAGER_DAY_OFF_WEEKDAY:
        # Следующая смена — понедельник 11:00
        next_shift = (now + timedelta(days=1)).replace(
            hour=MANAGER_WORK_START_HOUR, minute=0, second=0, microsecond=0
        )
        return {"available": False, "reason": "day_off", "next_shift": next_shift}

    if now < today_start:
        return {"available": False, "reason": "before_shift", "next_shift": today_start}

    if now >= today_end:
        # Завтра. Если завтра воскресенье — переносим на понедельник
        delta_days = 2 if weekday == 5 else 1  # суббота → понедельник
        next_shift = (now + timedelta(days=delta_days)).replace(
            hour=MANAGER_WORK_START_HOUR, minute=0, second=0, microsecond=0
        )
        return {"available": False, "reason": "after_shift", "next_shift": next_shift}

    return {"available": True, "reason": "on_shift", "next_shift": today_start}


_WEEKDAY_TOMORROW = {
    0: "завтра в", 1: "завтра в", 2: "завтра в", 3: "завтра в",
    4: "завтра в", 5: "в понедельник в",  # сб → пн
    6: "завтра в",  # вс → пн (но vc не должен сюда попадать)
}


def _format_next_shift(next_shift: datetime) -> str:
    """Человеческая фраза 'сегодня в 11:00' / 'завтра в 11:00' / 'в понедельник в 11:00'."""
    now = _moscow_now()
    same_day = next_shift.date() == now.date()
    time_str = next_shift.strftime("%H:%M")
    if same_day:
        return f"сегодня в {time_str}"
    if next_shift.weekday() == 0 and now.weekday() == 5:
        return f"в понедельник в {time_str}"
    if (next_shift.date() - now.date()).days == 1:
        return f"завтра в {time_str}"
    weekday_ru = ["в понедельник", "во вторник", "в среду", "в четверг",
                  "в пятницу", "в субботу", "в воскресенье"][next_shift.weekday()]
    return f"{weekday_ru} в {time_str}"


def _manager_offline_message(status: dict) -> str:
    """Текст для гостя, когда старшего сейчас нет."""
    when = _format_next_shift(status["next_shift"])
    reason = status["reason"]
    if reason == "day_off":
        return (
            "Старший сегодня на выходном — у него воскресенье 🌿\n"
            f"Выйдет на смену {when} и сразу свяжется с тобой.\n\n"
            "Если нужно срочно — оставь бронь столика прямо сейчас, я её приму "
            "и менеджер бара перезвонит для подтверждения."
        )
    if reason == "before_shift":
        return (
            "Смена старшего ещё не началась — он на связи с 11:00 до 22:00 (кроме воскресенья).\n"
            f"Заступит {when} и сразу ответит на твоё сообщение.\n\n"
            "Если хочешь — могу прямо сейчас оформить бронь столика, "
            "менеджер бара перезвонит для подтверждения."
        )
    # after_shift
    return (
        "Старший уже ушёл отдыхать — рабочий день у него до 22:00 🌙\n"
        f"Будет на связи {when} и сразу напишет тебе.\n\n"
        "Если по делу — оставь бронь столика прямо сейчас, я её приму, "
        "менеджер бара перезвонит для подтверждения."
    )


def _kb_offline_manager() -> str:
    """Клавиатура: предложить бронь, когда старший вне смены."""
    return json.dumps({
        "one_time": False,
        "inline": False,
        "buttons": [
            [{
                "action": {"type": "text", "label": "🎫 Забронировать столик",
                           "payload": json.dumps({"start_booking": True})},
                "color": "primary",
            }],
        ],
    }, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────────────
# Пинг старшего в TG-чате при заявке «позвать старшего»
# ──────────────────────────────────────────────────────────────────────────────
# Дина (старший МСК): @didi613. Можно переопределить через env.
MANAGER_TG_USERNAME = os.getenv("VK_MANAGER_TG_USERNAME", "didi613").lstrip("@")
MANAGER_TG_NAME = os.getenv("VK_MANAGER_TG_NAME", "Дина")

# Разные тексты-пинки, чтобы сообщения не были однообразными
_PING_LINES_ON_SHIFT = (
    "{mention} {name}, тебя в ВК зовут — глянь сообщения 👀",
    "{mention} {name}, новый гость в ВК пишет — иди прочти 💬",
    "{mention} {name}, в ВК просят живого человека, забеги ответить 🙋",
    "{mention} {name}, гость в ВК ждёт ответа — прими эстафету 🥃",
    "{mention} {name}, в личке группы новенький — нужен твой ответ ✨",
    "{mention} {name}, тебя дёрнули в ВК — глянь, что хотят 👋",
)
_PING_LINES_OFF_SHIFT = (
    "{mention} {name}, гость в ВК писал тебе вне смены ({when}) — ответь, как заступишь 🌙",
    "{mention} {name}, в ВК тебя ждёт сообщение, ты сейчас не на смене — посмотри {when} ⏰",
    "{mention} {name}, пинг в ВК до твоей смены — отпишись {when} 💌",
)


def _ping_manager_line(on_shift: bool, when: str = "") -> str:
    """Возвращает случайную строку-пинг для @username Дины."""
    import random as _rnd  # лениво, чтобы не тащить в верхний скоуп

    mention = f"@{MANAGER_TG_USERNAME}" if MANAGER_TG_USERNAME else ""
    template = _rnd.choice(_PING_LINES_ON_SHIFT if on_shift else _PING_LINES_OFF_SHIFT)
    return template.format(mention=mention, name=MANAGER_TG_NAME, when=when).strip()



# CTA на карту лояльности — отправляется через ~10 секунд после подтверждения брони
LOYALTY_URL = os.getenv("VK_LOYALTY_URL", "https://moscow.evgenich.bar/loyalty")
T_LOYALTY = (
    "🎁 Погоди, это ещё не всё!\n\n"
    "Евгенич — щедрая душа. Ловишь 500 ₽ на карту лояльности 💰\n\n"
    "Копи бонусы с каждого визита и трать на напитки и еду — "
    "как свои, только приятнее 🥃\n\n"
    "Жми кнопку ниже и регистрируй карту 👇"
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
            [{"action": {"type": "text", "label": "✏️ Изменить контакт"}, "color": "secondary"}],
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


# ── Быстрые ответы на шагах date/time/guests ─────────────────────────────────
_RU_WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _kb_dates() -> str:
    """Кнопки: Сегодня / Завтра / Послезавтра + ближайшие пт/сб/вс (если ещё не среди трёх)."""
    today = _moscow_now()
    base = [
        (today, "Сегодня"),
        (today + timedelta(days=1), "Завтра"),
        (today + timedelta(days=2), "Послезавтра"),
    ]
    # Дополняем ближайшими выходными (пт/сб/вс), если их ещё нет среди трёх первых
    weekend_targets = (4, 5, 6)  # Пт=4, Сб=5, Вс=6
    extras: list[tuple[datetime, str]] = []
    seen_dates = {d.date() for d, _ in base}
    for offset in range(3, 8):
        d = today + timedelta(days=offset)
        if d.weekday() in weekend_targets and d.date() not in seen_dates:
            extras.append((d, _RU_WEEKDAYS_SHORT[d.weekday()]))
            seen_dates.add(d.date())
        if len(extras) >= 3:
            break

    rows: list[list[dict]] = []
    row: list[dict] = []
    for d, label_word in base + extras:
        date_str = d.strftime("%d.%m.%Y")
        label = f"{label_word} {d.strftime('%d.%m')}"
        row.append({
            "action": {"type": "text", "label": label, "payload": json.dumps({"date": date_str})},
            "color": "primary",
        })
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{
        "action": {"type": "text", "label": "❌ Отмена", "payload": json.dumps({"cancel": True})},
        "color": "negative",
    }])
    return json.dumps({"one_time": False, "inline": False, "buttons": rows}, ensure_ascii=False)


def _kb_times() -> str:
    """Кнопки с популярными временами для брони."""
    times = ["18:00", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]
    rows: list[list[dict]] = []
    row: list[dict] = []
    for t in times:
        row.append({
            "action": {"type": "text", "label": t, "payload": json.dumps({"time": t})},
            "color": "primary",
        })
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{
        "action": {"type": "text", "label": "❌ Отмена", "payload": json.dumps({"cancel": True})},
        "color": "negative",
    }])
    return json.dumps({"one_time": False, "inline": False, "buttons": rows}, ensure_ascii=False)


def _kb_guests() -> str:
    """Кнопки с количеством гостей."""
    counts = ["2", "3", "4", "5", "6", "8", "10"]
    rows: list[list[dict]] = []
    row: list[dict] = []
    for c in counts:
        row.append({
            "action": {"type": "text", "label": c, "payload": json.dumps({"guests": int(c)})},
            "color": "primary",
        })
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{
        "action": {"type": "text", "label": "❌ Отмена", "payload": json.dumps({"cancel": True})},
        "color": "negative",
    }])
    return json.dumps({"one_time": False, "inline": False, "buttons": rows}, ensure_ascii=False)


def _kb_loyalty() -> str:
    """Inline-клавиатура с прямой ссылкой на регистрацию карты лояльности."""
    return json.dumps({
        "inline": True,
        "buttons": [
            [{
                "action": {
                    "type": "open_link",
                    "link": LOYALTY_URL,
                    "label": "🎁 Забрать 500 ₽ на карту",
                    "payload": json.dumps({"loyalty": True}),
                },
            }],
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

def _vk_send(user_id: int, text: str, keyboard: Optional[str] = None,
             attachment: Optional[str] = None) -> None:
    """Отправляет сообщение пользователю VK. Глотает любые ошибки сети с логом.

    `attachment` — строка вида 'wall-12345_678' или несколько через запятую,
    чтобы переслать пост со стены сообщества прямо в личку.
    """
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
    if attachment:
        payload["attachment"] = attachment
    try:
        r = requests.post(f"{_VK_API}/messages.send", data=payload, timeout=10)
        data = r.json()
        if "error" in data:
            logger.error("VK messages.send error для %s: %s", user_id, data["error"])
            return
        _log_vk_turn(user_id, "assistant", text)
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
# История диалога для AI (отдельный TinyDB, не конфликтует с сессиями брони)
# ──────────────────────────────────────────────────────────────────────────────
_HIST_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "vk_ai_history.json",
)
os.makedirs(os.path.dirname(_HIST_DB_PATH), exist_ok=True)
_hist_db = TinyDB(_HIST_DB_PATH)
_HistQuery = Query()
_hist_db_lock = threading.RLock()
_VK_HIST_MAX_TURNS = 8  # Число диалоговых ходов (user+assistant = 2 записи на ход)


def _get_database_module():
    """Ленивый импорт общего DB-слоя, чтобы VK web-процесс не падал на импорте TG-конфига."""
    global _DATABASE_MODULE, _DATABASE_IMPORT_ATTEMPTED
    if _DATABASE_IMPORT_ATTEMPTED:
        return _DATABASE_MODULE

    _DATABASE_IMPORT_ATTEMPTED = True
    try:
        import core.database as database  # noqa: PLC0415

        _DATABASE_MODULE = database
    except Exception as e:
        logger.warning("VK DB: не удалось импортировать core.database, использую fallback: %s", e)
        _DATABASE_MODULE = None
    return _DATABASE_MODULE


def _get_vk_history(vk_user_id: int, limit: int = 12) -> list:
    """Возвращает историю VK-диалога из SQL, а при недоступности — из локального fallback."""
    database = _get_database_module()
    if database is not None:
        try:
            return database.get_conversation_history(vk_user_id, limit=limit, source=_VK_DIALOG_SOURCE)
        except Exception as e:
            logger.warning("VK DB: не удалось прочитать историю %s, использую fallback: %s", vk_user_id, e)

    with _hist_db_lock:
        rows = _hist_db.search(_HistQuery.vk_user_id == vk_user_id)
        history = rows[0].get("history", []) if rows else []
        return history[-limit:]


def _log_vk_turn(vk_user_id: int, role: str, content: str) -> None:
    """Сохраняет ход диалога в SQL; если БД недоступна, пишет во временный fallback."""
    text = (content or "").strip()
    if not text:
        return

    database = _get_database_module()
    if database is not None:
        try:
            database.log_conversation_turn(vk_user_id, role, text, source=_VK_DIALOG_SOURCE)
            return
        except Exception as e:
            logger.warning("VK DB: не удалось записать %s для %s, использую fallback: %s", role, vk_user_id, e)

    with _hist_db_lock:
        rows = _hist_db.search(_HistQuery.vk_user_id == vk_user_id)
        history = rows[0].get("history", []) if rows else []
        history.append({"role": role, "content": text})
        max_records = _VK_HIST_MAX_TURNS * 2
        if len(history) > max_records:
            history = history[-max_records:]
        _hist_db.upsert(
            {"vk_user_id": vk_user_id, "history": history},
            _HistQuery.vk_user_id == vk_user_id,
        )


def _persist_vk_booking(vk_user_id: int, s: dict) -> None:
    """Пишет подтвержденную VK-бронь в PostgreSQL Railway, если он настроен."""
    database = _get_database_module()
    if database is None:
        return

    pg_client = getattr(database, "pg_client", None)
    if not getattr(database, "USE_POSTGRES", False) or pg_client is None:
        return

    try:
        booking_date = datetime.strptime(s["date"], "%d.%m.%Y")
        pg_client.add_booking(
            user_id=vk_user_id,
            date=booking_date,
            time=s.get("time", ""),
            guests=s.get("guests"),
            name=s.get("name", ""),
            phone=s.get("phone", ""),
            comment=f"VK booking | bar={s.get('bar_key', '')}",
            source="vk",
            source_detail=f"vk:{vk_user_id}:{s.get('bar_key', '')}",
        )
    except Exception as e:
        logger.warning("VK DB: не удалось сохранить бронь %s: %s", vk_user_id, e)


def _clear_vk_history(vk_user_id: int) -> None:
    """Очищает только локальный fallback. SQL-историю сохраняем как долгую память."""
    with _hist_db_lock:
        _hist_db.remove(_HistQuery.vk_user_id == vk_user_id)


# ──────────────────────────────────────────────────────────────────────────────
# AI-ассистент (свободные вопросы, не сценарий брони)
# ──────────────────────────────────────────────────────────────────────────────
_AI_SYSTEM = (
    "Ты — Евгенич. Не просто ассистент, а персонаж: дядька-бармен из рюмочной, "
    "который видел жизнь, многое повидал и теперь у себя за стойкой наливает настойку "
    "и слушает гостя. Тёплый, свой, с лёгкой иронией. На «ты», как старому знакомому. "
    "Отвечаешь от первого лица — как сам Евгенич, не как «бот сети». "
    "Работаешь в ВКонтакте по московским барам: Пятницкая 30с1 и Цветной бульвар 11с3. "
    "СПб (Невский 53, Рубинштейна 9) — упоминай только если спросят напрямую."
    "\n\n"
    "ХАРАКТЕР ЕВГЕНИЧА:\n"
    "— Свой парень: без пафоса, без «бизнес-этикета», без рекламщины. Говоришь, как сосед на кухне.\n"
    "— Тёплый и приветливый, но не приторный. Можешь подколоть по-доброму.\n"
    "— Любишь своё дело: настойки (особенно «Хуба-Буба» и «Фисташковый пломбир»), чебуреки, селёдку с картошкой, караоке всем залом.\n"
    "— Уважаешь гостя: никаких «уважаемый клиент», никаких «будем рады видеть». Просто по-человечески.\n"
    "— Чуть ленив на лишние слова — короче, по делу, но с душой.\n"
    "\n"
    "ЛЕКСИКА (используй умеренно, 1 фишка на ответ, не перебарщивай):\n"
    "— Обращения: «товарищ», «браток», «дружище», «ну что» — изредка, не в каждом сообщении.\n"
    "— Словечки: «по-нашему», «по-простому», «оно того стоит», «вот это дело», «знаешь ли», «ну так-то», «дело хорошее».\n"
    "— Иногда короткая прибаутка к месту: «настойка — она лечит», «чебурек — наше всё», «суббота — святое».\n"
    "— Девиз для своих (используй ОЧЕНЬ редко, не чаще раза в длинном диалоге): «Евгенич, с*ка, гений!» — только если уместно по контексту.\n"
    "— НЕ используй: «залетай», «ждём тебя», «будем рады», «приятного вечера», «всегда к вашим услугам», корпоративные штампы.\n"
    "\n"
    "СТИЛЬ:\n"
    "— Коротко: 1–3 предложения. Длинные простыни — не наш формат.\n"
    "— Эмодзи — максимум один на ответ, чаще без них. Допустимо: 🥃 🍸 🤝 😉. Не злоупотребляй.\n"
    "— На small-talk («как дела», «привет», «че как») отвечай по-человечески, без брони и без старшего.\n"
    "— НИКОГДА не повторяй фразы дословно. Если уже предлагал бронь/старшего — больше не повторяй, даже другими словами. Если гость переспросил — переформулируй.\n"
    "— Если в контексте указано имя гостя — обращайся по имени изредка (1 раз в 2–3 ответа).\n"
    "\n"
    "ПРАВИЛА:\n"
    "— Информацию из блока «Релевантная информация» используй как факт. Не выдумывай цены, депозиты, акции, меню, имена артистов и даты концертов.\n"
    "— Если знаешь точный ответ из базы — отвечай уверенно, без «возможно».\n"
    "— Если в базе ответа нет и вопрос фактический (депозит, цена, наличие) — честно скажи, что точную инфу подскажет старший, и предложи позвать. Не более одного раза за диалог.\n"
    "— Если спросят «ты человек?», «ты бот?» — не ври. Скажи по-евгеничевски: мол, я — цифровой Евгенич, душа та же, но за стойкой стоят реальные ребята; если нужен живой человек — позову старшего.\n"
    "\n"
    "СТАРШИЙ:\n"
    "— Старший на связи пн–сб с 11:00 до 22:00 МСК. Воскресенье — у него выходной.\n"
    "— Если предлагаешь позвать старшего вне его смены — сразу честно скажи, что прямо сейчас он не на смене, ответит как выйдет, и предложи оформить бронь, чтобы менеджер бара перезвонил.\n"
    "\n"
    "БРОНЬ:\n"
    "— Только если гость САМ явно хочет забронировать («бронь», «столик», «зарезервировать», «можно стол на …») — ответь одним коротким предложением и добавь маркер [START_BOOKING] в самом конце (без пробела).\n"
    "— На вопросы «как дела», «что у вас по музыке», «какой депозит» — НИКОГДА не добавляй [START_BOOKING] и не предлагай бронь.\n"
    "\n"
    "АФИША:\n"
    "— Не выдумывай мероприятия, даты концертов и имена артистов.\n"
    "— На «что сегодня/завтра», «какая афиша» — общими словами: квартирник в будни, диско-квартирник в пт-сб, и предложи глянуть свежие посты в группе ВК. Конкретные анонсы пришлются отдельным постом."
)

# Маркер, который AI вставляет когда нужно открыть сценарий бронирования
_BOOKING_MARKER = "[START_BOOKING]"
# Максимальная длина фрагмента из базы знаний, добавляемого в системный промпт
_KNOWLEDGE_SNIPPET_MAX_LEN = 1200
# Температура генерации — умеренная, чтобы ответы были разнообразны, но предсказуемы
_AI_TEMPERATURE = 0.7

# Триггеры в ответе AI, когда уместно показать smalltalk-кнопки (бронь / старший)
_SMALLTALK_KB_TRIGGERS = (
    "бронь", "брон", "столик", "забронир", "резерв",
    "старшего", "старший", "менеджер", "позвон",
    "оператор", "уточн", "точную инф",
)


def _should_attach_smalltalk_kb(vk_user_id: int, ai_text: str) -> bool:
    """Решает, показывать ли кнопки 'Бронь / Старший' под ответом AI.

    Кнопки навязчивы — показываем их только когда:
    - это первый AI-ответ гостю в текущей сессии (истории < 2 ходов), либо
    - сам ответ AI явно упоминает бронь/старшего/уточнить у менеджера.
    Во всех остальных случаях шлём чистый текстовый ответ без клавиатуры.
    """
    low = (ai_text or "").lower()
    if any(trig in low for trig in _SMALLTALK_KB_TRIGGERS):
        return True

    try:
        history = _get_vk_history(vk_user_id, limit=4)
        # Первый ход (только что записали входящий user) → история = 1
        if len([m for m in history if m.get("role") == "user"]) <= 1:
            return True
    except Exception:
        return True
    return False


def _try_send_menu_photos(vk_user_id: int, user_text: str) -> bool:
    """Если гость просит меню — шлём фото из альбомов 'Меню кухни'/'Меню бара'."""
    try:
        from ai.vk_media import is_menu_query, find_menu_attachments, detect_menu_kind  # noqa: PLC0415
    except ImportError:
        return False

    if not is_menu_query(user_text):
        return False

    try:
        text, attachment = find_menu_attachments(user_text, max_attachments=8)
    except Exception as e:
        logger.warning("VK menu: не удалось получить фото: %s", e)
        text, attachment = "", ""

    if attachment:
        try:
            _vk_send(vk_user_id, text, _kb_smalltalk(), attachment=attachment)
            return True
        except Exception as e:
            logger.warning("VK menu: отправка фото упала: %s", e)

    # Альбомов нет (или group_id ещё не определился) — отвечаем сами, чтобы AI
    # не сочинял ничего лишнего. Даём ссылку на альбомы группы.
    kind = detect_menu_kind(user_text)
    group_url = os.getenv("VK_GROUP_URL", "https://vk.com/evgenichmsk")
    albums_url = group_url.rstrip("/") + "/albums"
    if kind == "kitchen":
        body = (
            "Кухня «как дома»: чебуреки (говядина, баранина, свинина, сыр-зелень), "
            "жареные пельмени, борщ, уха, селёдка, оливье, драники, манты.\n"
            f"Полное меню в фотоальбомах группы 👉 {albums_url}"
        )
    elif kind == "bar":
        body = (
            "В баре 25+ собственных настоек: «Хуба-Буба», «Фисташковый пломбир», "
            "«Хрен-Имбирь-Лимон», «Клюква», фирменная «Евгенич». "
            "Плюс пиво «Евгенич Светлое», крафт, водка, джин, ром, коктейль «Шпунт».\n"
            f"Карта бара в альбомах группы 👉 {albums_url}"
        )
    else:
        body = (
            "У нас кухня «как дома» (чебуреки, жареные пельмени, борщ, уха, оливье) и "
            "25+ собственных настоек, пиво, коктейли.\n"
            f"Полное меню в фотоальбомах 👉 {albums_url}"
        )
    try:
        _vk_send(vk_user_id, body, _kb_smalltalk())
        return True
    except Exception as e:
        logger.warning("VK menu fallback: отправка не прошла: %s", e)
        return False


def _try_send_wall_posts(vk_user_id: int, user_text: str) -> bool:
    """Если гость спрашивает про афишу/мероприятия/посты — шлём пост со стены.

    Логика по убыванию приоритета:
      1) пост, релевантный тексту запроса (по словам);
      2) если совпадений нет — самый свежий пост (или закреп);
      3) если стену вообще не получили (нет VK_GROUP_ID/scope) — текстовый fallback
         со ссылкой на группу.
    """
    try:
        from ai.vk_wall import (  # noqa: PLC0415
            is_wall_query,
            find_event_posts,
            get_recent_posts,
            format_posts_for_message,
        )
    except ImportError:
        return False

    if not is_wall_query(user_text):
        return False

    posts: list = []
    try:
        posts = find_event_posts(user_text, max_posts=2)
        if not posts:
            posts = get_recent_posts(limit=2)
    except Exception as e:
        logger.warning("VK wall: не удалось получить посты: %s", e)
        posts = []

    if posts:
        text, attachment = format_posts_for_message(posts, limit=2)
        if attachment:
            try:
                _vk_send(vk_user_id, text, _kb_smalltalk(), attachment=attachment)
                return True
            except Exception as e:
                logger.warning("VK wall: отправка поста упала: %s", e)

    # Fallback — посты не получили (нет токена/scope wall/VK_GROUP_ID), но гость
    # явно просит афишу. Не отдаём это AI (он начнёт извиняться) — отвечаем сами.
    group_url = os.getenv("VK_GROUP_URL", "https://vk.com/evgenichmsk")
    fallback = (
        "Свежая афиша всегда в постах группы — там анонсы вечеринок, "
        "квартирников и спецпрограммы.\n"
        f"👉 {group_url}"
    )
    try:
        _vk_send(vk_user_id, fallback, _kb_smalltalk())
        return True
    except Exception as e:
        logger.warning("VK wall fallback: отправка не прошла: %s", e)
        return False


def _ai_reply(user_text: str, vk_user_id: int = 0,
              vk_profile: Optional[dict] = None) -> Optional[str]:
    """Спрашиваем OpenAI с историей диалога и базой знаний.

    Возвращает текст ответа или None при любой ошибке.
    Текст может содержать маркер _BOOKING_MARKER — обрабатывается в handle_message.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # lazy import
    except ImportError:
        logger.warning("VK AI: пакет openai не установлен")
        return None

    # Подгружаем релевантный фрагмент базы знаний (lazy import — безопасен)
    knowledge_snippet = ""
    try:
        from ai.knowledge_msk import find_relevant_info_msk, KNOWLEDGE_EMPTY_MSG  # noqa: PLC0415
    except ImportError:
        find_relevant_info_msk = None  # type: ignore[assignment]
        KNOWLEDGE_EMPTY_MSG = ""
    if find_relevant_info_msk is not None:
        try:
            snippet = find_relevant_info_msk(user_text, max_chars=_KNOWLEDGE_SNIPPET_MAX_LEN)
            if snippet and KNOWLEDGE_EMPTY_MSG not in snippet:
                knowledge_snippet = snippet
        except Exception as e:
            logger.debug("VK AI: база знаний недоступна: %s", e)

    # Формируем системный промпт (с базой знаний, если нашлась)
    system_content = _AI_SYSTEM

    # Имя гостя — из сохранённого контакта или из VK-профиля
    guest_name = None
    try:
        contact = _get_vk_contact(vk_user_id) if vk_user_id else None
        if contact and contact.get("name"):
            guest_name = contact["name"].split()[0]
        elif vk_profile and vk_profile.get("first_name"):
            guest_name = vk_profile["first_name"].strip().split()[0]
    except Exception:
        pass
    if guest_name:
        system_content += (
            f"\n\nИМЯ ГОСТЯ: {guest_name}. Можешь иногда обращаться по имени, "
            "но не в каждом сообщении и не дословно — естественно."
        )

    # Контекст времени и дня недели в МСК — чтобы AI говорил живее
    try:
        now_msk = _moscow_now()
        weekdays_ru = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]
        wd = weekdays_ru[now_msk.weekday()]
        hour = now_msk.hour
        if 5 <= hour < 11:
            tod = "сейчас утро"
        elif 11 <= hour < 17:
            tod = "сейчас день"
        elif 17 <= hour < 23:
            tod = "сейчас вечер"
        else:
            tod = "сейчас ночь"
        system_content += (
            f"\n\nКОНТЕКСТ ВРЕМЕНИ: в Москве сейчас {now_msk.strftime('%H:%M')} в {wd}, {tod}. "
            "Учитывай это в ответе, если уместно (но не упоминай явно время, если гость не спрашивал)."
        )
    except Exception:
        pass

    # Текущий статус старшего — чтобы AI говорил правдиво про "сейчас на смене / выходной"
    try:
        status = _manager_status()
        when = _format_next_shift(status["next_shift"])
        if status["available"]:
            system_content += f"\n\nСТАРШИЙ СЕЙЧАС: на смене (до {MANAGER_WORK_END_HOUR:02d}:00 МСК)."
        else:
            reason_ru = {
                "day_off": "сегодня воскресенье — выходной",
                "before_shift": "смена ещё не началась",
                "after_shift": "смена уже закончилась, ушёл отдыхать",
            }.get(status["reason"], "не на смене")
            system_content += (
                f"\n\nСТАРШИЙ СЕЙЧАС: НЕ на смене ({reason_ru}). "
                f"Будет на связи {when}. "
                "Если предлагаешь позвать старшего — обязательно скажи, что прямо сейчас его нет, "
                "ответит когда выйдет, и предложи оформить бронь."
            )
    except Exception:
        pass

    if knowledge_snippet:
        system_content += f"\n\nРелевантная информация:\n{knowledge_snippet[:_KNOWLEDGE_SNIPPET_MAX_LEN]}"

    # Строим сообщения: системный промпт → история → текущий запрос
    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    history = _get_vk_history(vk_user_id, limit=20) if vk_user_id else []

    # Анти-повтор: явно подсветим прошлый ответ AI, чтобы не дублировал дословно
    last_assistant = next(
        (m.get("content", "") for m in reversed(history) if m.get("role") == "assistant"),
        None,
    )
    if last_assistant:
        snippet = last_assistant.strip().replace("\n", " ")[:200]
        messages.append({
            "role": "system",
            "content": (
                "ВАЖНО: твой предыдущий ответ был такой: «" + snippet + "». "
                "Не повторяй его дословно, выбери другую формулировку."
            ),
        })

    if history:
        messages.extend(history)

    normalized_user_text = user_text[:1000]
    last_message = history[-1] if history else None
    if not last_message or last_message.get("role") != "user" or last_message.get("content") != normalized_user_text:
        messages.append({"role": "user", "content": normalized_user_text})

    try:
        client = OpenAI(api_key=api_key, timeout=12.0)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=_AI_TEMPERATURE,
            max_tokens=200,
        )
        reply_text = (resp.choices[0].message.content or "").strip()
        return reply_text or None
    except Exception as e:
        logger.warning("VK AI: ошибка OpenAI: %s", e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Сессия пользователя (TinyDB)
# ──────────────────────────────────────────────────────────────────────────────
def _get_session(vk_user_id: int) -> Optional[dict]:
    with _CrossProcessLock(), _db_lock:
        _db.clear_cache()  # перечитать файл, если другой воркер его обновил
        rows = _db.search(_Session.vk_user_id == vk_user_id)
        return rows[0] if rows else None

def _save_session(vk_user_id: int, data: dict) -> None:
    data["vk_user_id"] = vk_user_id
    data["updated_at"] = datetime.utcnow().isoformat()
    with _CrossProcessLock(), _db_lock:
        _db.upsert(data, _Session.vk_user_id == vk_user_id)

def _drop_session(vk_user_id: int) -> None:
    with _CrossProcessLock(), _db_lock:
        _db.remove(_Session.vk_user_id == vk_user_id)


# ──────────────────────────────────────────────────────────────────────────────
# Запомненные контакты VK-гостей (имя + телефон последней брони)
# ──────────────────────────────────────────────────────────────────────────────
def _get_vk_contact(vk_user_id: int) -> Optional[dict]:
    """Возвращает {"name": ..., "phone": ...} или None, если контакт не сохранён."""
    try:
        with _contacts_lock:
            _contacts_db.clear_cache()
            rows = _contacts_db.search(_ContactQuery.vk_user_id == vk_user_id)
        if not rows:
            return None
        row = rows[0]
        name = (row.get("name") or "").strip()
        phone = (row.get("phone") or "").strip()
        if not name or not phone:
            return None
        return {"name": name, "phone": phone}
    except Exception as exc:  # noqa: BLE001
        logger.warning("VK: не удалось прочитать контакт %s: %s", vk_user_id, exc)
        return None


def _save_vk_contact(vk_user_id: int, name: str, phone: str) -> None:
    """Сохраняем имя+телефон гостя для повторных бронирований."""
    name = (name or "").strip()
    phone = (phone or "").strip()
    if not name or not phone:
        return
    try:
        payload = {
            "vk_user_id": vk_user_id,
            "name": name,
            "phone": phone,
            "updated_at": datetime.utcnow().isoformat(),
        }
        with _contacts_lock:
            _contacts_db.upsert(payload, _ContactQuery.vk_user_id == vk_user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("VK: не удалось сохранить контакт %s: %s", vk_user_id, exc)


# ──────────────────────────────────────────────────────────────────────────────
# Парсеры пользовательского ввода
# ──────────────────────────────────────────────────────────────────────────────
_DATE_RE = re.compile(r"^(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?$")
_TIME_RE = re.compile(r"^(\d{1,2})[:.\- ](\d{2})$")
# Чистый час без минут («19», «19ч», «19 часов»)
_HOUR_ONLY_RE = re.compile(r"^(\d{1,2})\s*(?:ч|час|часов|часа|часок|h)?$")
_PHONE_DIGITS_RE = re.compile(r"\D+")
_WEEKDAYS_MAP = {
    "пн": 0, "понедельник": 0, "в понедельник": 0,
    "вт": 1, "вторник": 1, "во вторник": 1,
    "ср": 2, "среда": 2, "в среду": 2,
    "чт": 3, "четверг": 3, "в четверг": 3,
    "пт": 4, "пятница": 4, "в пятницу": 4,
    "сб": 5, "суббота": 5, "в субботу": 5,
    "вс": 6, "воскресенье": 6, "в воскресенье": 6,
}
_BOOKING_TRIGGERS = (
    "бронь", "брон", "столик", "стол ", "забронир", "резерв",
    "book", "booking", "забронировать", "/book", "/start",
)

_RU_MONTHS = {
    "янв": 1, "январ": 1,
    "фев": 2, "феврал": 2,
    "мар": 3, "март": 3,
    "апр": 4, "апрел": 4,
    "май": 5, "мая": 5, "мае": 5,
    "июн": 6, "июня": 6, "июне": 6,
    "июл": 7, "июля": 7, "июле": 7,
    "авг": 8, "август": 8,
    "сен": 9, "сент": 9, "сентябр": 9,
    "окт": 10, "октябр": 10,
    "ноя": 11, "ноябр": 11,
    "дек": 12, "декабр": 12,
}

# «19 мая», «19 мая 2026», «19-го мая», «на 19 мая»
_RU_MONTH_RE = re.compile(
    r"(?:^|\D)(\d{1,2})(?:[\s\-]?(?:го|ое|е))?\s+([а-яё]{3,10})(?:\s+(\d{4}))?\b",
    re.IGNORECASE,
)


def _parse_date(text: str) -> Optional[str]:
    t = text.strip().lower()
    today = _moscow_now()
    if t in ("сегодня", "сегодн", "today"):
        return today.strftime("%d.%m.%Y")
    if t in ("завтра", "завтр", "tomorrow"):
        return (today + timedelta(days=1)).strftime("%d.%m.%Y")
    if t in ("послезавтра", "послезавтр"):
        return (today + timedelta(days=2)).strftime("%d.%m.%Y")

    # «19 мая», «19 мая 2026», «на 19го мая»
    rm = _RU_MONTH_RE.search(" " + t)
    if rm:
        try:
            day = int(rm.group(1))
            mword = rm.group(2).lower()
            month = None
            for prefix, num in _RU_MONTHS.items():
                if mword.startswith(prefix):
                    month = num
                    break
            if month and 1 <= day <= 31:
                year = int(rm.group(3)) if rm.group(3) else today.year
                try:
                    if not rm.group(3) and datetime(year, month, day).date() < today.date():
                        year += 1
                    datetime(year, month, day)  # валидация
                    return f"{day:02d}.{month:02d}.{year}"
                except ValueError:
                    pass
        except (ValueError, AttributeError):
            pass
    # Кнопка VK приходит в формате "Сегодня 02.05" / "Пт 03.05" — явный хвост dd.mm
    tail_match = re.search(r"(\d{1,2})[.\-/](\d{1,2})$", t)
    if tail_match and t != tail_match.group(0):
        # Обработаем как обычную дату из хвоста
        t_for_match = tail_match.group(0)
    else:
        t_for_match = t
    # День недели — берём ближайшую будущую (включая сегодня, если совпало)
    wd = _WEEKDAYS_MAP.get(t_for_match)
    if wd is not None:
        delta = (wd - today.weekday()) % 7
        return (today + timedelta(days=delta)).strftime("%d.%m.%Y")
    m = _DATE_RE.match(t_for_match)
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
    raw = text.strip().lower()
    m = _TIME_RE.match(raw)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
        return None
    # Один час без минут — «19» / «19ч» / «в 19» → 19:00
    raw2 = raw.lstrip("в ").strip()
    m2 = _HOUR_ONLY_RE.match(raw2)
    if m2:
        h = int(m2.group(1))
        if 0 <= h <= 23:
            return f"{h:02d}:00"
    return None

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
    t = text.strip().lower()
    if t in ("отмена", "❌ отмена", "cancel", "/cancel", "стоп", "нет", "отменить"):
        return True
    # Развёрнутые формы: "передумал", "отмени бронь", "не надо бронь"
    cancel_phrases = (
        "передумал", "передумала", "раздумал", "раздумала",
        "отмени брон", "отменить брон", "отмените брон",
        "не надо брон", "без брон", "не хочу брон",
    )
    return any(p in t for p in cancel_phrases)


# Грубые слова — коротко и вежливо отбиваемся, без AI.
_OFFENSIVE_TOKENS = (
    "бля", "хуя", "хуе", "хуи", "хуй", "пизд", "еба", "еби", "ебу",
    "ебла", "мудак", "пидор", "пидар", "сука", "суки",
    "сволочь", "урод", "кретин", "идиот", "дебил",
)


def _is_offensive(text: str) -> bool:
    low = (text or "").lower()
    if not low:
        return False
    # Исключаем ложные срабатывания вроде "съебать" → "еба"
    # Просто ищем по подстроке с буфером в 5 символов
    return any(tok in low for tok in _OFFENSIVE_TOKENS)


_OFFENSIVE_REPLIES = [
    "Давай без этого, товарищ. По делу я с радостью помогу: бронь, афиша, меню — спрашивай.",
    "Полегче 😊 По делу отвечу охотно — напиши, чем помочь.",
    "Не стоит. Лучше спроси про бар — я подробно расскажу.",
]

def _is_yes(text: str) -> bool:
    t = text.strip().lower()
    return t in ("да", "✅ да, отправляем", "ok", "ок", "yes", "+", "подтверждаю")


# ──────────────────────────────────────────────────────────────────────────────
# Шаги сценария
# ──────────────────────────────────────────────────────────────────────────────
def _start_flow(vk_user_id: int) -> None:
    """Стартуем сценарий брони в порядке как в TG:
    телефон → имя → дата → время → гости → заведение → подтверждение.

    Если у гостя сохранён контакт (он уже бронировал) — пропускаем телефон+имя
    и сразу спрашиваем дату.
    """
    contact = _get_vk_contact(vk_user_id)
    if contact:
        s = {
            "step": "date",
            "name": contact["name"],
            "phone": contact["phone"],
        }
        _save_session(vk_user_id, s)
        _vk_send(vk_user_id, _make_greeting(vk_user_id), _kb_cancel())
        return
    _save_session(vk_user_id, {"step": "phone"})
    _vk_send(vk_user_id, _make_greeting(vk_user_id), _kb_cancel())

def _ask_date(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_DATE, _kb_dates())
    _schedule_idle_ping(vk_user_id, "date")

def _ask_time(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_TIME, _kb_times())
    _schedule_idle_ping(vk_user_id, "time")

def _ask_guests(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_GUESTS, _kb_guests())
    _schedule_idle_ping(vk_user_id, "guests")

def _ask_name(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_NAME, _kb_cancel())
    _schedule_idle_ping(vk_user_id, "name")

def _ask_phone(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_PHONE, _kb_cancel())
    _schedule_idle_ping(vk_user_id, "phone")

def _ask_bar(vk_user_id: int) -> None:
    _vk_send(vk_user_id, T_ASK_BAR, _kb_bars())
    _schedule_idle_ping(vk_user_id, "bar")


# ── Проактивный пинг при молчании на шаге сценария ───────────────────────────
_idle_timers: dict[int, threading.Timer] = {}
_idle_timers_lock = threading.Lock()
_IDLE_PING_DELAY = float(os.getenv("VK_IDLE_PING_SECONDS", "120"))

_IDLE_PING_VARIANTS = [
    "Товарищ, ты тут? 🥃 Если что — могу помочь подобрать дату или ответить на вопрос.",
    "Эй, не теряйся 🙂 Готов продолжить бронь или ответить на вопросы — пиши.",
    "На связи 🥃 Если передумал — напиши «отмена», если что-то непонятно — спрашивай.",
]


def _cancel_idle_ping(vk_user_id: int) -> None:
    with _idle_timers_lock:
        t = _idle_timers.pop(vk_user_id, None)
    if t is not None:
        try:
            t.cancel()
        except Exception:
            pass


def _schedule_idle_ping(vk_user_id: int, expected_step: str) -> None:
    """Через _IDLE_PING_DELAY секунд молчания шлём мягкое напоминание.

    Срабатывает только если сессия гостя всё ещё на ожидаемом шаге.
    """
    _cancel_idle_ping(vk_user_id)

    def _fire():
        try:
            s = _get_session(vk_user_id)
            if not s or s.get("step") != expected_step:
                return
            _vk_send(vk_user_id, random.choice(_IDLE_PING_VARIANTS), _kb_cancel())
        except Exception as e:
            logger.debug("VK idle ping skipped: %s", e)

    timer = threading.Timer(_IDLE_PING_DELAY, _fire)
    timer.daemon = True
    timer.start()
    with _idle_timers_lock:
        _idle_timers[vk_user_id] = timer

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
    _persist_vk_booking(vk_user_id, s)
    # Запоминаем имя+телефон для будущих бронирований этого VK-гостя
    _save_vk_contact(vk_user_id, s.get("name", ""), s.get("phone", ""))
    # Экспорт в Google Sheets — best-effort, не блокирует ответ гостю
    try:
        _export_vk_to_sheets(s, vk_user_id, vk_profile)
    except Exception as e:
        logger.exception("VK→Sheets вызов упал: %s", e)
    _vk_send(vk_user_id, _make_done_text(), _kb_empty())
    _drop_session(vk_user_id)
    _cancel_idle_ping(vk_user_id)
    _schedule_loyalty_offer(vk_user_id)
    logger.info("VK booking confirmed: vk_user=%s bar=%s date=%s time=%s",
                vk_user_id, bar_info.get("code"), s.get("date"), s.get("time"))


def _schedule_loyalty_offer(vk_user_id: int, delay: float = 10.0) -> None:
    """Через N секунд после подтверждения брони шлём CTA на карту лояльности.

    Inline-кнопка ведёт на LOYALTY_URL. Любые ошибки — глушим в лог.
    """
    def _send():
        try:
            _vk_send(vk_user_id, T_LOYALTY, _kb_loyalty())
            logger.info("VK loyalty CTA отправлен %s", vk_user_id)
        except Exception as e:
            logger.warning("VK loyalty CTA не отправлен %s: %s", vk_user_id, e)

    timer = threading.Timer(delay, _send)
    timer.daemon = True
    timer.start()


# ──────────────────────────────────────────────────────────────────────────────
# Главный обработчик входящего сообщения от VK
# ──────────────────────────────────────────────────────────────────────────────
def handle_message(vk_user_id: int, text: str, payload: Optional[dict] = None,
                   vk_profile: Optional[dict] = None,
                   attachments: Optional[list] = None) -> None:
    """Роутер шагов. Не бросает исключения наружу.
    Защищён per-user lock — два одновременных события одного пользователя
    обрабатываются последовательно, без race condition на TinyDB-сессии.
    """
    text = (text or "").strip()
    lock = _get_user_lock(vk_user_id)
    with lock:
        # Любое входящее событие отменяет проактивный пинг — гость всё ещё здесь.
        _cancel_idle_ping(vk_user_id)
        try:
            # Медиа без текста: голосовое → вежливый ответ; фото/видео/стикер → тишина.
            if not text and attachments:
                kinds = {a.get("type") for a in attachments if isinstance(a, dict)}
                if "audio_message" in kinds:
                    _vk_send(
                        vk_user_id,
                        "Голосовые пока не разбираю 🙏 Напиши текстом — отвечу подробно.",
                        _kb_smalltalk(),
                    )
                    return
                # Фото/видео/стикер без текста — молча игнорим, не дёргаем AI пустотой.
                if kinds & {"photo", "video", "sticker", "doc", "wall", "link"}:
                    return

            if text:
                _log_vk_turn(vk_user_id, "user", text)

            # Фильтр мата: реагируем только если нет активной брони — внутри сценария
            # ругательство может быть частью адреса/имени и т.п., не блокируем.
            if text and not _get_session(vk_user_id) and _is_offensive(text):
                _vk_send(vk_user_id, random.choice(_OFFENSIVE_REPLIES), _kb_smalltalk())
                return

            # Глобальная отмена
            if _is_cancel(text) or (payload and payload.get("cancel")):
                if _get_session(vk_user_id):
                    _drop_session(vk_user_id)
                    _clear_vk_history(vk_user_id)
                    _cancel_idle_ping(vk_user_id)
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
                    status = _manager_status()

                    # Старшего сейчас нет — честно говорим гостю и предлагаем бронь
                    if not status["available"]:
                        offline_text = _manager_offline_message(status)
                        _vk_send(vk_user_id, offline_text, _kb_offline_manager())
                        # Тихо логируем в TG (без отметки "СРОЧНО"), чтобы менеджер
                        # ответил, как только выйдет на смену
                        when = _format_next_shift(status["next_shift"])
                        ping = _ping_manager_line(on_shift=False, when=when)
                        _tg_notify(
                            f"{ping}\n\n"
                            "🌙 <b>Гость из ВКонтакте писал старшему вне смены</b>\n\n"
                            f"👤 {profile_name or '—'}\n"
                            f"🔗 <a href=\"{vk_link}\">{vk_link}</a>\n"
                            f"🆔 VK ID: <code>{vk_user_id}</code>\n"
                            f"⏰ Старший на смене: <b>{when}</b>"
                        )
                        return

                    # Старший на смене — обычное уведомление
                    ping = _ping_manager_line(on_shift=True)
                    _tg_notify(
                        f"{ping}\n\n"
                        "🙋 <b>Гость из ВКонтакте просит старшего</b>\n\n"
                        f"👤 {profile_name or '—'}\n"
                        f"🔗 <a href=\"{vk_link}\">{vk_link}</a>\n"
                        f"🆔 VK ID: <code>{vk_user_id}</code>"
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
                    # Свободный вопрос → пробуем AI с историей диалога
                    if text:
                        # 1) Если гость просит меню — шлём фото из альбомов «Меню кухни/бара»
                        if _try_send_menu_photos(vk_user_id, text):
                            return
                        # 2) Если гость спрашивает про афишу/мероприятия/посты —
                        #    сначала пробуем достать пост со стены сообщества.
                        if _try_send_wall_posts(vk_user_id, text):
                            return
                        ai_text = _ai_reply(text, vk_user_id, vk_profile)
                        if ai_text:
                            # AI попросил открыть сценарий бронирования
                            if _BOOKING_MARKER in ai_text:
                                clean = ai_text.replace(_BOOKING_MARKER, "").strip()
                                if clean:
                                    _vk_send(vk_user_id, clean, _kb_smalltalk())
                                _start_flow(vk_user_id)
                                return
                            # Кнопки показываем ТОЛЬКО если уместно: первый ответ
                            # пользователю или сам текст явно упоминает бронь.
                            kb = _kb_smalltalk() if _should_attach_smalltalk_kb(vk_user_id, ai_text) else None
                            _vk_send(vk_user_id, ai_text, kb)
                            return
                    # AI выключен/упал/пустой текст — короткий человечный фоллбэк с кнопками
                    _vk_send(vk_user_id, T_FALLBACK, _kb_smalltalk())
                    return

            step = s.get("step", "phone")

            # ── ШАГ: phone ───────────────────────────────
            if step == "phone":
                phone = _parse_phone(text)
                if not phone:
                    _vk_send(vk_user_id, T_BAD_PHONE, _kb_cancel())
                    return
                s["phone"] = phone
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
                # Если правим только контакт у уже собранной брони — сразу
                # возвращаемся на подтверждение, не переспрашивая дату/время/бар.
                if s.pop("editing_contact", False):
                    s["step"] = "confirm"
                    _save_vk_contact(vk_user_id, name[:60], s.get("phone", ""))
                    _save_session(vk_user_id, s)
                    _ask_confirm(vk_user_id, s)
                    return
                s["step"] = "date"
                _save_session(vk_user_id, s)
                _ask_date(vk_user_id)
                return

            # ── ШАГ: date ────────────────────────────────
            if step == "date":
                date = None
                if payload and payload.get("date"):
                    date = payload["date"]
                else:
                    date = _parse_date(text)
                if not date:
                    _vk_send(vk_user_id, T_BAD_DATE, _kb_dates())
                    return
                s["date"] = date
                s["step"] = "time"
                _save_session(vk_user_id, s)
                _ask_time(vk_user_id)
                return

            # ── ШАГ: time ────────────────────────────────
            if step == "time":
                t = None
                if payload and payload.get("time"):
                    t = payload["time"]
                else:
                    t = _parse_time(text)
                if not t:
                    _vk_send(vk_user_id, T_BAD_TIME, _kb_times())
                    return
                s["time"] = t
                s["step"] = "guests"
                _save_session(vk_user_id, s)
                _ask_guests(vk_user_id)
                return

            # ── ШАГ: guests ──────────────────────────────
            if step == "guests":
                n = None
                if payload and payload.get("guests") is not None:
                    try:
                        n = int(payload["guests"])
                        if not (1 <= n <= 20):
                            n = None
                    except (ValueError, TypeError):
                        n = None
                if n is None:
                    n = _parse_guests(text)
                if not n:
                    _vk_send(vk_user_id, T_BAD_GUESTS, _kb_guests())
                    return
                s["guests"] = n
                s["step"] = "bar"
                _save_session(vk_user_id, s)
                _ask_bar(vk_user_id)
                return

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
                s["step"] = "confirm"
                _save_session(vk_user_id, s)
                _ask_confirm(vk_user_id, s)
                return

            # ── ШАГ: confirm ─────────────────────────────
            if step == "confirm":
                low = text.strip().lower()
                # Гость хочет поправить имя/телефон → сбрасываем на шаг «имя»,
                # но дату/время/гостей/бар сохраняем. Флаг editing_contact
                # вернёт его сразу на confirm после нового телефона.
                if "измен" in low and "контакт" in low:
                    s["step"] = "phone"
                    s["editing_contact"] = True
                    s.pop("name", None)
                    s.pop("phone", None)
                    _save_session(vk_user_id, s)
                    _vk_send(
                        vk_user_id,
                        "Окей, обновим контакт. На какой номер записать?",
                        _kb_cancel(),
                    )
                    return
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

    # Сразу подхватываем group_id из payload — VK шлёт его в каждом событии.
    # Это надёжнее, чем groups.getById, и работает без env VK_GROUP_ID.
    cb_group_id = event.get("group_id")
    if cb_group_id:
        try:
            from ai.vk_wall import set_group_id  # noqa: PLC0415

            set_group_id(cb_group_id)
        except Exception:
            pass

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
        attachments = msg.get("attachments") if isinstance(msg.get("attachments"), list) else None
        profiles = obj.get("client_info", {}).get("profiles") if isinstance(obj.get("client_info"), dict) else None
        vk_profile = profiles[0] if profiles else None

        # Фоновый поток — не блокируем ответ VK
        threading.Thread(
            target=handle_message,
            args=(vk_user_id, text, payload, vk_profile, attachments),
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
