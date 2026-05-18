"""
Универсальный helper отправки брони в внешний webhook (n8n → AmoCRM).

Используется TG (handlers/booking_flow.py), VK (handlers/vk_bot.py),
Instagram (handlers/instagram_bot.py — пока шлёт сам, формат совместим).

ENV:
    BOOKING_WEBHOOK_URL — URL n8n. Если пусто — функция тихо ничего не делает.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_BOOKING_WEBHOOK_URL = os.getenv("BOOKING_WEBHOOK_URL", "").strip()
_RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT", "production")

_MSK_TZ = timezone(timedelta(hours=3))


def _msk_now() -> datetime:
    return datetime.now(_MSK_TZ)


def is_enabled() -> bool:
    return bool(_BOOKING_WEBHOOK_URL)


def send_booking(
    *,
    source: str,                          # "telegram" | "vk" | "instagram"
    medium: str,                          # "tg" | "vk" | "instagram"
    bar_key: str,                         # bar_pyatnitskaya | bar_tsvetnoj | bar_rubinstein | bar_nevsky | ...
    bar_label: str,                       # "🏛 Пятницкая 30с1"
    bar_city: str,                        # "Москва" | "Санкт-Петербург"
    amo_tag: str,                         # "ЕВГ_МСК_ПЯТ" / "ЕВГ_СПБ_РУБ" / ...
    date: str,                            # "20.05.2026"
    time_str: str,                        # "19:30"
    guests: Any,                          # int или str
    name: str,
    phone: str,
    comment: str = "",
    guest: Optional[dict] = None,         # дополнительные поля о госте
    extra: Optional[dict] = None,         # любые доп. поля (channel и т.п.)
    channel: Optional[dict] = None,       # {"id": "tg_bot", "name": "Telegram бот"}
    booking_id: Optional[str] = None,
    is_returning: bool = False,
    campaign: str = "guest_booking",
) -> None:
    """Шлёт payload в `BOOKING_WEBHOOK_URL` в отдельном потоке, не блокируя caller."""
    if not _BOOKING_WEBHOOK_URL:
        return

    now = _msk_now()
    bid = booking_id or f"{medium.upper()}-{int(time.time())}"

    payload: dict[str, Any] = {
        "event": "booking_created",
        "source": source,
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
        "utm": {
            "source": "smm",
            "medium": medium,
            "campaign": campaign,
            "content": f"{medium}_bot_guest_booking",
            "term": f"guest_{medium}",
        },
        "booking": {
            "id": bid,
            "bar_key": bar_key,
            "bar": bar_label,
            "bar_label": bar_label,
            "bar_city": bar_city,
            "amo_tag": amo_tag,
            "date": date,
            "time": time_str,
            "guests": guests,
            "name": name,
            "phone": phone,
            "comment": comment or "",
            "created_at_msk": now.strftime("%d.%m.%Y %H:%M МСК"),
            "created_at_iso": now.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
        },
        "guest": {
            "is_returning": is_returning,
            "name": name,
            "phone": phone,
            **(guest or {}),
        },
        "channel": channel or {"id": f"{medium}_bot", "name": f"{source} бот"},
        "meta": {"bot": "evgenich-gift", "env": _RAILWAY_ENV},
    }
    if extra:
        payload.update(extra)

    def _do() -> None:
        try:
            r = requests.post(_BOOKING_WEBHOOK_URL, json=payload, timeout=8)
            if r.status_code >= 400:
                logger.warning(
                    "Booking webhook %s returned HTTP %s: %s",
                    source, r.status_code, r.text[:200],
                )
            else:
                logger.info(
                    "Booking webhook OK: source=%s id=%s bar=%s status=%s",
                    source, bid, amo_tag, r.status_code,
                )
        except Exception as e:
            logger.warning("Booking webhook %s failed: %s", source, e)

    threading.Thread(
        target=_do, daemon=True, name=f"booking-webhook-{medium}-{bid}"
    ).start()
