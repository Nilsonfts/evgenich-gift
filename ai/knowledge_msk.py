# /ai/knowledge_msk.py
"""
Поиск релевантной информации по московской базе знаний (для VK-ассистента).

Главное отличие от ai/knowledge.find_relevant_info — ищем по СЕКЦИЯМ
(заголовки `## ...`), а не построчно. Это даёт ассистенту цельный кусок
контекста (например, всю секцию про депозит), а не оборванные строки.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from ai.knowledge_base_msk import KNOWLEDGE_BASE_MSK

KNOWLEDGE_EMPTY_MSG = "Точной информации в базе нет."

# Простой словарь синонимов, чтобы запросы вида "сколько стоит зайти" попадали
# в секцию "ДЕПОЗИТ И ВХОД", а "до скольки работаете" — в "ВРЕМЯ РАБОТЫ".
_SYNONYMS = {
    "депозит": ["депозит", "минималка", "минимальный заказ", "минимальный чек"],
    "вход": ["вход", "входной", "файс", "фейс-контроль", "пропуск", "плата за вход", "сколько стоит зайти"],
    "бронь": ["бронь", "брон", "забронир", "столик", "стол", "резерв", "забить"],
    "адрес": ["адрес", "где находитесь", "как добраться", "как доехать", "метро", "пятницкая", "цветной"],
    "время работы": ["время работы", "часы работы", "до скольки", "со скольки", "когда открыты", "когда закрываетесь", "график", "работаете", "открыты", "закрыт"],
    "кухня": ["кухня", "поесть", "еда", "меню", "чебурек", "пельмен", "борщ", "оливье", "покушать", "пожрать"],
    "напитки": ["настойк", "коктейл", "пиво", "водка", "джин", "ром", "виски", "лимонад", "шпунт", "выпить"],
    "цены": ["цена", "цены", "стоимость", "сколько стоит", "средний чек", "чек", "дорого", "дёшево"],
    "караоке": ["караоке", "петь", "микрофон", "сцена"],
    "музыка": ["музык", "диджей", "диско", "тусовк", "танц"],
    "правила": ["дресс", "одежда", "что надеть", "запрет", "нельзя", "правила"],
    "оплата": ["оплат", "карт", "налич", "сбп", "перевод", "чаевые", "tips"],
    "животные": ["собак", "котик", "питом", "пет", "пускают с соб", "с собакой"],
    "дети": ["дети", "ребенок", "ребёнок", "ребят", "школьник"],
    "топ кухни": ["что взять", "что попробовать", "посоветуй", "хит", "вкусное", "вкусно", "что у вас вкусное"],
    "топ настоек": ["настойк", "хуба", "фисташковый", "клюква", "хрен"],
    "курение": ["курить", "курен", "кальян", "вейп"],
    "скидки": ["скидк", "акци", "день рождения", "бонус", "промокод"],
    "банкет": ["банкет", "корпоратив", "выкуп", "большая компания", "большой компании"],
    "афиша": ["афиша", "событие", "мероприят", "концерт", "выступл", "программа"],
    "парковка": ["парков", "припарк", "машин", "авто"],
}

# Слишком общие/служебные слова, которые не должны попадать в скоринг секций —
# иначе на «как дела» матчится что попало.
_STOP_WORDS = {
    "что", "как", "где", "когда", "куда", "кто", "это", "там", "тут", "дел", "дела",
    "вас", "тебя", "меня", "себе", "ваш", "наш", "мой", "твой", "его", "её",
    "для", "про", "над", "под", "при", "под", "без", "тоже", "также", "очень", "просто",
    "ещё", "еще", "уже", "потом", "теперь", "сейчас", "пока", "ну", "вот", "ага",
    "норм", "нормально", "ок", "окей", "спасибо", "привет", "здравствуйте", "здарова",
    "товарищ", "евгенич", "бар",
    "есть", "быть", "была", "были", "буду", "будет", "хочу", "хочешь", "надо", "нужно", "можно",
    "наверное", "может", "много", "мало",
    # Дни недели и общие временные слова — иначе «в пятницу» матчит чужие секции
    "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье",
    "пятницу", "субботу", "понедельника", "вторника", "среды", "четверга", "пятницы",
    "субботы", "воскресенья", "будни", "выходные", "сегодня", "завтра", "вечером", "утром",
    "днем", "днём", "ночью",
}


def _split_sections(text: str) -> List[Tuple[str, str]]:
    """Разбивает базу на секции вида (заголовок, тело).

    Заголовок — строка вида '## ...'. Текст до первой секции игнорируется.
    """
    sections: List[Tuple[str, str]] = []
    current_title: str | None = None
    current_lines: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped[3:].strip()
            current_lines = []
        else:
            if current_title is not None:
                current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return sections


_SECTIONS = _split_sections(KNOWLEDGE_BASE_MSK)
_WORD_RE = re.compile(r"[а-яёa-z0-9\-]+", re.IGNORECASE)


def _expand_query(query: str) -> List[str]:
    """Возвращает список ключевых слов с учётом синонимов и фильтра стоп-слов."""
    low = (query or "").lower()
    raw_tokens = set(_WORD_RE.findall(low))
    tokens: set[str] = set()

    for canonical, variants in _SYNONYMS.items():
        for v in variants:
            if v in low:
                tokens.add(canonical)
                tokens.update(t for t in _WORD_RE.findall(v) if len(t) >= 4)
                break

    for tok in raw_tokens:
        if len(tok) < 4:
            continue
        if tok in _STOP_WORDS:
            continue
        tokens.add(tok)

    return list(tokens)


def _score_section(title: str, body: str, tokens: List[str]) -> int:
    """Простой скоринг: сумма вхождений токенов в заголовок (×3) и тело (×1)."""
    if not tokens:
        return 0
    title_low = title.lower()
    body_low = body.lower()
    score = 0
    for tok in tokens:
        if tok in title_low:
            score += 3
        score += body_low.count(tok)
    return score


def find_relevant_info_msk(query: str, max_sections: int = 2, max_chars: int = 1200) -> str:
    """Возвращает наиболее релевантные секции базы знаний по МСК-барам.

    Если ничего не нашлось — возвращает KNOWLEDGE_EMPTY_MSG, чтобы вызывающий
    код мог надёжно понять, что контекста нет.
    """
    tokens = _expand_query(query)
    if not tokens:
        return KNOWLEDGE_EMPTY_MSG

    scored: List[Tuple[int, str, str]] = []
    for title, body in _SECTIONS:
        score = _score_section(title, body, tokens)
        if score > 0:
            scored.append((score, title, body))

    if not scored:
        return KNOWLEDGE_EMPTY_MSG

    scored.sort(key=lambda x: x[0], reverse=True)
    pieces: List[str] = []
    total = 0
    for _, title, body in scored[:max_sections]:
        block = f"## {title}\n{body}".strip()
        if total + len(block) > max_chars:
            block = block[: max(0, max_chars - total)]
        if not block:
            break
        pieces.append(block)
        total += len(block)
        if total >= max_chars:
            break

    return "\n\n".join(pieces) if pieces else KNOWLEDGE_EMPTY_MSG
