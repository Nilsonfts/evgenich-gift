"""
Тестовые отправки в n8n webhook AmoCRM для проверки маппинга полей.

Использование:
    python scripts/test_amocrm_webhook.py            # все 6 кейсов
    python scripts/test_amocrm_webhook.py tg         # только Telegram
    python scripts/test_amocrm_webhook.py vk         # только VKontakte
    python scripts/test_amocrm_webhook.py ig         # только Instagram
    python scripts/test_amocrm_webhook.py --url=<>   # переопределить URL

ENV:
    BOOKING_WEBHOOK_URL — переопределяет дефолтный URL n8n.

Каждый payload отправляется со всеми полями, которые шлёт реальный бот:
- source (telegram|vk|instagram)
- utm (source=smm, medium=tg|vk|instagram, campaign, content)
- guest (id, username, first_name, last_name, profile_url, phone)
- booking (bar_key, bar_label, amo_tag, date, time, guests, comment, created_at_msk)
- channel (id, name)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any

import requests

DEFAULT_URL = os.getenv(
    "BOOKING_WEBHOOK_URL",
    "https://n.govorovteam.ru/webhook/evg",
)


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _msk_now() -> str:
    # Москва = UTC+3, без зависимостей от tz-баз
    from datetime import timedelta, timezone
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M МСК")


# ────────────────────────────────────────────────────────────────────────────
# 1. Telegram — Москва, Пятницкая
# ────────────────────────────────────────────────────────────────────────────
TG_MSK_PYAT: dict[str, Any] = {
    "event": "booking_created",
    "source": "telegram",
    "utm": {
        "source": "smm",
        "medium": "tg",
        "campaign": "evgenich_msk",
        "content": "bot_booking",
    },
    "guest": {
        "id": 1234567890,
        "username": "test_guest_tg",
        "first_name": "Иван",
        "last_name": "Тестов",
        "profile_url": "https://t.me/test_guest_tg",
        "phone": "+79991234567",
        "is_returning": False,
    },
    "booking": {
        "bar_key": "bar_pyatnitskaya",
        "bar_label": "🏛 Пятницкая 30с1",
        "bar_city": "Москва",
        "amo_tag": "ЕВГ_МСК_ПЯТ",
        "date": "20.05.2026",
        "date_iso": "2026-05-20",
        "time": "19:30",
        "guests": 4,
        "name": "Иван Тестов",
        "phone": "+79991234567",
        "comment": "День рождения, нужен столик у окна",
        "created_at_msk": _msk_now(),
        "created_at_iso": _now_iso(),
    },
    "channel": {"id": "tg_bot", "name": "Telegram бот"},
    "_test": True,
}

# ────────────────────────────────────────────────────────────────────────────
# 2. Telegram — СПб, Рубинштейна (возвратный гость)
# ────────────────────────────────────────────────────────────────────────────
TG_SPB_RUB: dict[str, Any] = {
    "event": "booking_created",
    "source": "telegram",
    "utm": {"source": "smm", "medium": "tg", "campaign": "evgenich_spb", "content": "bot_booking"},
    "guest": {
        "id": 9876543210,
        "username": "olga_p",
        "first_name": "Ольга",
        "last_name": "Петрова",
        "profile_url": "https://t.me/olga_p",
        "phone": "+79261112233",
        "is_returning": True,
    },
    "booking": {
        "bar_key": "bar_rubinstein",
        "bar_label": "🥃 Евгенич на Рубинштейна 9",
        "bar_city": "Санкт-Петербург",
        "amo_tag": "ЕВГ_СПБ_РУБ",
        "date": "22.05.2026",
        "date_iso": "2026-05-22",
        "time": "21:00",
        "guests": 2,
        "name": "Ольга Петрова",
        "phone": "+79261112233",
        "comment": "Хочется уютный уголок",
        "created_at_msk": _msk_now(),
        "created_at_iso": _now_iso(),
    },
    "channel": {"id": "tg_bot", "name": "Telegram бот"},
    "_test": True,
}

# ────────────────────────────────────────────────────────────────────────────
# 3. VK — Москва, Цветной
# ────────────────────────────────────────────────────────────────────────────
VK_MSK_TSVET: dict[str, Any] = {
    "event": "booking_created",
    "source": "vk",
    "utm": {"source": "smm", "medium": "vk", "campaign": "evgenich_msk", "content": "vk_bot_booking"},
    "guest": {
        "id": 12345678,
        "username": "id12345678",
        "first_name": "Сергей",
        "last_name": "ВКашник",
        "profile_url": "https://vk.com/id12345678",
        "phone": "+79993334455",
        "is_returning": False,
    },
    "booking": {
        "bar_key": "bar_tsvetnoj",
        "bar_label": "🌸 Цветной бульвар 11с3",
        "bar_city": "Москва",
        "amo_tag": "ЕВГ_МСК_ЦВЕТ",
        "date": "19.05.2026",
        "date_iso": "2026-05-19",
        "time": "20:00",
        "guests": 6,
        "name": "Сергей ВКашник",
        "phone": "+79993334455",
        "comment": "День рождения друга, нужен большой стол",
        "created_at_msk": _msk_now(),
        "created_at_iso": _now_iso(),
    },
    "channel": {"id": "vk_bot", "name": "VK ЕВГЕНИЧ Москва"},
    "_test": True,
}

# ────────────────────────────────────────────────────────────────────────────
# 4. VK — Москва, Пятницкая (минимальный набор полей)
# ────────────────────────────────────────────────────────────────────────────
VK_MSK_PYAT: dict[str, Any] = {
    "event": "booking_created",
    "source": "vk",
    "utm": {"source": "smm", "medium": "vk", "campaign": "evgenich_msk"},
    "guest": {
        "id": 87654321,
        "username": "id87654321",
        "first_name": "Анна",
        "last_name": "К.",
        "profile_url": "https://vk.com/id87654321",
        "phone": "+79051112233",
        "is_returning": True,
    },
    "booking": {
        "bar_key": "bar_pyatnitskaya",
        "bar_label": "🏛 Пятницкая 30с1",
        "bar_city": "Москва",
        "amo_tag": "ЕВГ_МСК_ПЯТ",
        "date": "21.05.2026",
        "date_iso": "2026-05-21",
        "time": "19:00",
        "guests": 2,
        "name": "Анна К.",
        "phone": "+79051112233",
        "comment": "",
        "created_at_msk": _msk_now(),
        "created_at_iso": _now_iso(),
    },
    "channel": {"id": "vk_bot", "name": "VK ЕВГЕНИЧ Москва"},
    "_test": True,
}

# ────────────────────────────────────────────────────────────────────────────
# 5. Instagram — Москва, Цветной
# ────────────────────────────────────────────────────────────────────────────
IG_MSK_TSVET: dict[str, Any] = {
    "event": "booking_created",
    "source": "instagram",
    "utm": {"source": "smm", "medium": "instagram", "campaign": "evgenich_msk", "content": "ig_dm_booking"},
    "guest": {
        "id": "17841400000000111",
        "username": "ig_test_user",
        "first_name": "Мария",
        "last_name": "",
        "profile_url": "https://instagram.com/ig_test_user",
        "phone": "+79161234567",
        "is_returning": False,
    },
    "booking": {
        "bar_key": "bar_tsvetnoj",
        "bar_label": "🌸 Цветной бульвар 11с3",
        "bar_city": "Москва",
        "amo_tag": "ЕВГ_МСК_ЦВЕТ",
        "date": "23.05.2026",
        "date_iso": "2026-05-23",
        "time": "20:30",
        "guests": 3,
        "name": "Мария",
        "phone": "+79161234567",
        "comment": "Романтика, тихий стол",
        "created_at_msk": _msk_now(),
        "created_at_iso": _now_iso(),
    },
    "channel": {"id": "ig_dm", "name": "Instagram Direct"},
    "_test": True,
}

# ────────────────────────────────────────────────────────────────────────────
# 6. Instagram — Москва, Пятницкая
# ────────────────────────────────────────────────────────────────────────────
IG_MSK_PYAT: dict[str, Any] = {
    "event": "booking_created",
    "source": "instagram",
    "utm": {"source": "smm", "medium": "instagram", "campaign": "evgenich_msk"},
    "guest": {
        "id": "17841400000000222",
        "username": "another_ig",
        "first_name": "Дмитрий",
        "last_name": "",
        "profile_url": "https://instagram.com/another_ig",
        "phone": "+79257778899",
        "is_returning": False,
    },
    "booking": {
        "bar_key": "bar_pyatnitskaya",
        "bar_label": "🏛 Пятницкая 30с1",
        "bar_city": "Москва",
        "amo_tag": "ЕВГ_МСК_ПЯТ",
        "date": "24.05.2026",
        "date_iso": "2026-05-24",
        "time": "22:00",
        "guests": 5,
        "name": "Дмитрий",
        "phone": "+79257778899",
        "comment": "Компания, караоке",
        "created_at_msk": _msk_now(),
        "created_at_iso": _now_iso(),
    },
    "channel": {"id": "ig_dm", "name": "Instagram Direct"},
    "_test": True,
}


CASES = {
    "tg_msk_pyat": TG_MSK_PYAT,
    "tg_spb_rub": TG_SPB_RUB,
    "vk_msk_tsvet": VK_MSK_TSVET,
    "vk_msk_pyat": VK_MSK_PYAT,
    "ig_msk_tsvet": IG_MSK_TSVET,
    "ig_msk_pyat": IG_MSK_PYAT,
}

GROUPS = {
    "tg": ["tg_msk_pyat", "tg_spb_rub"],
    "vk": ["vk_msk_tsvet", "vk_msk_pyat"],
    "ig": ["ig_msk_tsvet", "ig_msk_pyat"],
    "all": list(CASES.keys()),
}


def _send(url: str, name: str, payload: dict) -> None:
    print(f"\n── {name} → {url}")
    print(f"   source={payload['source']} | medium={payload['utm'].get('medium')} | "
          f"bar={payload['booking']['bar_key']} | amo_tag={payload['booking']['amo_tag']}")
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"   HTTP {r.status_code}")
        body = r.text[:400].strip()
        if body:
            print(f"   body: {body}")
    except Exception as e:
        print(f"   ERROR: {e}")


def main() -> int:
    url = DEFAULT_URL
    group = "all"

    for arg in sys.argv[1:]:
        if arg.startswith("--url="):
            url = arg.split("=", 1)[1]
        elif arg in GROUPS:
            group = arg
        elif arg in CASES:
            group = arg

    if group in CASES:
        names = [group]
    else:
        names = GROUPS[group]

    print(f"AMO webhook test → {url}")
    print(f"Cases ({len(names)}): {', '.join(names)}\n")
    print("Payload schema (общий для всех):")
    print(json.dumps(CASES[names[0]], ensure_ascii=False, indent=2))

    for n in names:
        _send(url, n, CASES[n])

    print("\nГотово.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
