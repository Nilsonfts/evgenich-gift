"""
Уровни лояльности Евгенича.

Маппинг "k_bonus" (% кэшбэка из GMB) → читаемый уровень + прогресс до следующего.

Бизнес-правила (из карты лояльности рюмочной):
    ТОВАРИЩ      — 5%   стартовый
    ИНТЕЛЛИГЕНТ  — 10%  при сумме покупок от 40 000 ₽
    БУРЖУЙ       — 15%  при сумме покупок от 100 000 ₽

Источник данных:
    Из ответа GMB find_client_by_phone берём:
      - client.totalAmount  — суммарные траты в ₽ (нарастающий итог)
      - client.k_bonus      — текущий % кэшбэка (как fallback, если totalAmount нет)
"""

from typing import Optional, Dict, Tuple


# ── Конфигурация уровней ──
# Порядок ВАЖЕН: от младшего к старшему. Поле threshold_amount — нижняя граница в ₽.
LEVELS = [
    {
        "code": "tovarishch",
        "name": "ТОВАРИЩ",
        "emoji": "🤝",
        "k_bonus": 5,
        "threshold_amount": 0,
        "description": "Свой человек у барной стойки",
    },
    {
        "code": "intelligent",
        "name": "ИНТЕЛЛИГЕНТ",
        "emoji": "🎩",
        "k_bonus": 10,
        "threshold_amount": 40_000,
        "description": "Заходишь регулярно, разбираешься в настойках",
    },
    {
        "code": "burzhuy",
        "name": "БУРЖУЙ",
        "emoji": "💎",
        "k_bonus": 15,
        "threshold_amount": 100_000,
        "description": "Почётный гражданин нашей рюмочной",
    },
]


def get_level_by_total(total_amount: float) -> Dict:
    """
    Возвращает текущий уровень по сумме покупок.

    >>> get_level_by_total(0)['name']
    'ТОВАРИЩ'
    >>> get_level_by_total(50000)['name']
    'ИНТЕЛЛИГЕНТ'
    >>> get_level_by_total(150000)['name']
    'БУРЖУЙ'
    """
    try:
        amount = float(total_amount or 0)
    except (TypeError, ValueError):
        amount = 0.0

    current = LEVELS[0]
    for level in LEVELS:
        if amount >= level["threshold_amount"]:
            current = level
        else:
            break
    return current


def get_level_by_k_bonus(k_bonus: int) -> Dict:
    """
    Fallback-определение уровня по % кэшбэка (если totalAmount недоступен).
    """
    try:
        k = int(k_bonus or 0)
    except (TypeError, ValueError):
        k = 0
    for level in reversed(LEVELS):
        if k >= level["k_bonus"]:
            return level
    return LEVELS[0]


def get_progress_to_next(total_amount: float) -> Optional[Dict]:
    """
    Прогресс до следующего уровня.

    Returns:
        {
            'next_level': dict,
            'remaining_amount': int,    # ₽ до следующей ступени
            'progress_percent': int,    # 0..99 (если 100 — уже на след. уровне)
            'current_amount': int,
        }
        либо None, если уже на максимальном уровне.
    """
    try:
        amount = float(total_amount or 0)
    except (TypeError, ValueError):
        amount = 0.0

    current = get_level_by_total(amount)
    current_idx = LEVELS.index(current)

    # Уже на топовом уровне
    if current_idx >= len(LEVELS) - 1:
        return None

    next_level = LEVELS[current_idx + 1]
    floor = current["threshold_amount"]
    ceiling = next_level["threshold_amount"]
    span = max(1, ceiling - floor)
    progressed = max(0, amount - floor)
    pct = min(99, int(progressed * 100 / span))

    return {
        "next_level": next_level,
        "remaining_amount": max(0, int(ceiling - amount)),
        "progress_percent": pct,
        "current_amount": int(amount),
    }


def render_progress_bar(percent: int, width: int = 10) -> str:
    """Рисует ASCII прогресс-бар: ▓▓▓▓▓░░░░░"""
    try:
        p = max(0, min(100, int(percent)))
    except (TypeError, ValueError):
        p = 0
    filled = int(p * width / 100)
    return "▓" * filled + "░" * (width - filled)


def format_money(amount) -> str:
    """1234567 → '1 234 567 ₽'"""
    try:
        n = int(float(amount or 0))
    except (TypeError, ValueError):
        n = 0
    return f"{n:,} ₽".replace(",", " ")


def detect_level_upgrade(prev_code: Optional[str], current_code: str) -> Optional[Tuple[Dict, Dict]]:
    """
    Определяет, был ли апгрейд уровня.

    Args:
        prev_code: code предыдущего уровня (из БД), может быть None
        current_code: code текущего уровня

    Returns:
        (prev_level, current_level) если апгрейд произошёл, иначе None.
        Возвращает None если prev_code is None (первая фиксация — не считаем апгрейдом).
    """
    if not prev_code or prev_code == current_code:
        return None
    codes = [lvl["code"] for lvl in LEVELS]
    if prev_code not in codes or current_code not in codes:
        return None
    if codes.index(current_code) > codes.index(prev_code):
        prev_level = next(l for l in LEVELS if l["code"] == prev_code)
        cur_level = next(l for l in LEVELS if l["code"] == current_code)
        return (prev_level, cur_level)
    return None


def get_level_card_text(
    name: str,
    balance: int,
    total_amount: float,
    k_bonus: Optional[int] = None,
    max_pay_pct: Optional[int] = None,
) -> str:
    """
    Готовый блок текста для экрана «Карта лояльности».

    Возвращает HTML-форматированный текст с уровнем, прогрессом и условиями.
    """
    # Определяем уровень — приоритет totalAmount, fallback на k_bonus
    if total_amount and total_amount > 0:
        level = get_level_by_total(total_amount)
    elif k_bonus:
        level = get_level_by_k_bonus(k_bonus)
    else:
        level = LEVELS[0]

    actual_k = k_bonus or level["k_bonus"]

    lines = [
        f"🎁 <b>Карта лояльности «Евгенич»</b>",
        "",
        f"👤 {name or 'Товарищ'}",
        f"{level['emoji']} Уровень: <b>{level['name']}</b> — {actual_k}% кэшбэка",
        f"💰 Баланс: <b>{int(balance or 0)} бонусов</b>",
    ]

    if total_amount:
        lines.append(f"📊 Накоплено покупок: <b>{format_money(total_amount)}</b>")

    if max_pay_pct:
        lines.append(f"💳 Оплата бонусами: до {max_pay_pct}% от заказа")

    # Прогресс до следующего уровня
    progress = get_progress_to_next(total_amount or 0)
    if progress:
        nxt = progress["next_level"]
        bar = render_progress_bar(progress["progress_percent"])
        lines.extend([
            "",
            f"<b>До «{nxt['name']}» {nxt['emoji']} ({nxt['k_bonus']}%):</b>",
            f"<code>{bar}</code> {progress['progress_percent']}%",
            f"Осталось: {format_money(progress['remaining_amount'])}",
        ])
    else:
        lines.extend([
            "",
            f"🏆 <b>Ты на максимальном уровне!</b>",
            f"Уважают, наливают первым, без очереди.",
        ])

    return "\n".join(lines)


def get_upgrade_congratulation(prev: Dict, current: Dict, name: str = "Товарищ") -> str:
    """Поздравительное сообщение при апгрейде уровня (в духе Евгенича)."""
    return (
        f"🎺 <b>{name}, тебя повышают в звании!</b>\n\n"
        f"Был {prev['emoji']} <b>{prev['name']}</b> — стал {current['emoji']} "
        f"<b>{current['name']}</b>.\n\n"
        f"С этой минуты — <b>{current['k_bonus']}%</b> кэшбэка с каждой рюмки. "
        f"Заслужил.\n\n"
        f"<i>{current['description']}.</i>"
    )
