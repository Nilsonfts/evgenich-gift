# /ai/vk_wall.py
"""
Чтение стены сообщества Евгенич через VK API (`wall.get`) с кэшем в памяти.

Используется VK-ассистентом, чтобы отвечать на вопросы про афишу, мероприятия
и свежие посты, и пересылать сам пост гостю как `attachment=wall<owner>_<id>`
в `messages.send`.

Окружение:
    VK_GROUP_TOKEN  — токен сообщества (с правами wall, messages)
    VK_GROUP_ID     — ID сообщества (число, без минуса). Если не задан, попробуем
                      определить через `groups.getById` по токену.

Кэш живёт ~5 минут, чтобы не долбить VK API на каждый вопрос.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_VK_API = "https://api.vk.com/method"
_VK_VERSION = "5.199"

# Сколько постов забираем со стены (все типы — закреп, обычные, реклама)
_WALL_FETCH_COUNT = 20
# TTL кэша постов (секунды)
_CACHE_TTL = 300
# Сколько постов максимум возвращаем для AI/афиши
_MAX_RESULT_POSTS = 3

_cache_lock = threading.Lock()
_posts_cache: dict[str, Any] = {"ts": 0.0, "owner_id": 0, "posts": []}
_group_id_cache: Optional[int] = None

# Слова-триггеры, по которым гость спрашивает про афишу/посты/события
EVENT_KEYWORDS = (
    "афиш", "мероприят", "событи", "программ", "что сегодня", "что завтра",
    "что у вас в", "что у вас на", "пост", "стен", "анонс", "розыгр",
    "выступ", "концерт", "вечеринк", "тусовк", "диско", "квартирник",
    "когда диско", "какие планы",
)


def _get_token() -> str:
    return os.getenv("VK_GROUP_TOKEN", "") or ""


def _resolve_group_id() -> int:
    """Определяет числовой ID сообщества: либо из env, либо через groups.getById."""
    global _group_id_cache
    if _group_id_cache:
        return _group_id_cache

    env_id = os.getenv("VK_GROUP_ID", "").strip()
    if env_id:
        try:
            _group_id_cache = abs(int(env_id))
            return _group_id_cache
        except ValueError:
            logger.warning("VK_GROUP_ID не число: %r", env_id)

    token = _get_token()
    if not token:
        return 0
    try:
        r = requests.get(
            f"{_VK_API}/groups.getById",
            params={"access_token": token, "v": _VK_VERSION},
            timeout=10,
        )
        data = r.json()
        if "error" in data:
            logger.warning("VK groups.getById error: %s", data["error"])
            return 0
        groups = data.get("response", {}).get("groups") or data.get("response") or []
        if isinstance(groups, list) and groups:
            gid = int(groups[0].get("id", 0))
            if gid:
                _group_id_cache = gid
                return gid
    except Exception as e:
        logger.warning("VK groups.getById упал: %s", e)
    return 0


def _fetch_wall(force: bool = False) -> list[dict]:
    """Возвращает свежие посты со стены сообщества (с кэшем 5 минут)."""
    now = time.time()
    with _cache_lock:
        if not force and (now - _posts_cache["ts"] < _CACHE_TTL) and _posts_cache["posts"]:
            return _posts_cache["posts"]

    token = _get_token()
    gid = _resolve_group_id()
    if not token or not gid:
        return []

    owner_id = -gid
    try:
        r = requests.get(
            f"{_VK_API}/wall.get",
            params={
                "access_token": token,
                "v": _VK_VERSION,
                "owner_id": owner_id,
                "count": _WALL_FETCH_COUNT,
                "filter": "owner",
                "extended": 0,
            },
            timeout=10,
        )
        data = r.json()
        if "error" in data:
            logger.warning("VK wall.get error: %s", data["error"])
            return []
        items = data.get("response", {}).get("items", []) or []
    except Exception as e:
        logger.warning("VK wall.get упал: %s", e)
        return []

    posts: list[dict] = []
    for it in items:
        if it.get("marked_as_ads"):
            continue
        text = (it.get("text") or "").strip()
        post_id = it.get("id")
        if not post_id:
            continue
        posts.append({
            "id": post_id,
            "owner_id": owner_id,
            "date": int(it.get("date") or 0),
            "text": text,
            "is_pinned": bool(it.get("is_pinned")),
            "has_photo": any(
                a.get("type") == "photo" for a in (it.get("attachments") or [])
            ),
            "url": f"https://vk.com/wall{owner_id}_{post_id}",
            "attachment_ref": f"wall{owner_id}_{post_id}",
        })

    # Сортируем по дате, но закреп идёт первым
    posts.sort(key=lambda p: (not p["is_pinned"], -p["date"]))

    with _cache_lock:
        _posts_cache["ts"] = now
        _posts_cache["owner_id"] = owner_id
        _posts_cache["posts"] = posts

    return posts


def is_wall_query(text: str) -> bool:
    """Похоже ли сообщение на вопрос про афишу/мероприятия/посты сообщества."""
    if not text:
        return False
    low = text.lower()
    return any(kw in low for kw in EVENT_KEYWORDS)


_TOKEN_RE = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


def _score_post(post: dict, tokens: list[str]) -> int:
    """Скоринг поста: вхождения токенов запроса в текст + бонус за свежесть."""
    text_low = (post.get("text") or "").lower()
    if not text_low:
        return 0
    score = 0
    for tok in tokens:
        if len(tok) < 3:
            continue
        if tok in text_low:
            score += 2
    # Бонус за «событийные» слова
    for kw in ("сегодня", "завтра", "пятниц", "суббот", "афиш", "мероприят",
               "вечеринк", "квартирник", "концерт", "выступ"):
        if kw in text_low:
            score += 1
    # Свежие посты ценнее (бонус, если пост моложе 30 дней)
    if post.get("date") and (time.time() - post["date"]) < 30 * 86400:
        score += 1
    return score


def find_event_posts(query: str = "", max_posts: int = _MAX_RESULT_POSTS) -> list[dict]:
    """Возвращает посты со стены, наиболее релевантные запросу.

    Если запрос пустой — возвращает закреп + последние посты.
    """
    posts = _fetch_wall()
    if not posts:
        return []

    if not query:
        return posts[:max_posts]

    tokens = [t for t in _TOKEN_RE.findall(query.lower()) if len(t) >= 3]
    scored = []
    for p in posts:
        s = _score_post(p, tokens)
        if s > 0:
            scored.append((s, p))
    if not scored:
        # Запрос явно событийный, но точных совпадений нет → отдаём свежие
        return posts[:max_posts]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_posts]]


def format_posts_for_message(posts: list[dict], limit: int = 3) -> tuple[str, str]:
    """Готовит текст и строку attachment для messages.send.

    Возвращает (text, attachments_csv).
    Текст — короткий комментарий + ссылки на посты, если их несколько.
    attachments_csv — например "wall-12345_678,wall-12345_679" (≤10).
    """
    if not posts:
        return "", ""
    chosen = posts[:limit]
    refs = [p["attachment_ref"] for p in chosen]
    if len(chosen) == 1:
        text = "Вот свежий пост по теме — там все детали:"
    else:
        text = "Лови пару свежих постов с афишей и анонсами:"
    return text, ",".join(refs)


def get_recent_posts(limit: int = 5) -> list[dict]:
    """Алиас для свежих постов без фильтрации по запросу."""
    return _fetch_wall()[:limit]
