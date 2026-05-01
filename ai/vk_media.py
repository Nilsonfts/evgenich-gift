# /ai/vk_media.py
"""
Чтение фото-альбомов и товаров сообщества Евгенич через VK API.

Используется VK-ассистентом для:
- ответа «меню кухни/бара» — берём фото из альбомов с такими названиями
- ответа «что есть в продаже / товары» — берём market.get
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import requests

from ai.vk_wall import _resolve_group_id, _get_token, _VK_API, _VK_VERSION

logger = logging.getLogger(__name__)

_CACHE_TTL = 600  # 10 минут — альбомы и товары меняются редко
_MAX_PHOTOS_PER_ALBUM = 10  # сколько фото максимум подгружаем из альбома
_MAX_SEND = 10  # VK limit: до 10 attachments в одном messages.send

_albums_cache: dict[str, object] = {"ts": 0.0, "albums": []}
_photos_cache: dict[int, dict] = {}
_market_cache: dict[str, object] = {"ts": 0.0, "items": []}
_cache_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
# Фото-альбомы (меню кухни / меню бара / интерьер)
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_albums(force: bool = False) -> list[dict]:
    """Возвращает все альбомы сообщества с названием и id."""
    now = time.time()
    with _cache_lock:
        cached = _albums_cache.get("albums") or []
        if not force and (now - float(_albums_cache.get("ts", 0)) < _CACHE_TTL) and cached:
            return cached  # type: ignore[return-value]

    token = _get_token()
    gid = _resolve_group_id()
    if not token or not gid:
        return []
    owner_id = -gid

    try:
        r = requests.get(
            f"{_VK_API}/photos.getAlbums",
            params={
                "access_token": token,
                "v": _VK_VERSION,
                "owner_id": owner_id,
                "need_system": 1,
                "need_covers": 0,
            },
            timeout=10,
        )
        data = r.json()
        if "error" in data:
            logger.warning("VK photos.getAlbums error: %s", data["error"])
            return []
        items = data.get("response", {}).get("items", []) or []
    except Exception as e:
        logger.warning("VK photos.getAlbums упал: %s", e)
        return []

    albums = [
        {
            "id": int(a.get("id", 0)),
            "owner_id": owner_id,
            "title": (a.get("title") or "").strip(),
            "size": int(a.get("size") or 0),
        }
        for a in items
        if a.get("id") is not None
    ]
    with _cache_lock:
        _albums_cache["ts"] = now
        _albums_cache["albums"] = albums
    logger.info("VK media: загружено %d альбомов", len(albums))
    return albums


def _fetch_album_photos(album_id: int, owner_id: int, count: int = _MAX_PHOTOS_PER_ALBUM) -> list[dict]:
    """Загружает первые N фото альбома (с кэшем)."""
    cache_key = album_id
    now = time.time()
    with _cache_lock:
        entry = _photos_cache.get(cache_key)
        if entry and (now - float(entry.get("ts", 0)) < _CACHE_TTL):
            return entry.get("photos", [])  # type: ignore[return-value]

    token = _get_token()
    if not token:
        return []
    try:
        r = requests.get(
            f"{_VK_API}/photos.get",
            params={
                "access_token": token,
                "v": _VK_VERSION,
                "owner_id": owner_id,
                "album_id": album_id,
                "count": count,
                "rev": 1,  # сначала свежие
            },
            timeout=10,
        )
        data = r.json()
        if "error" in data:
            logger.warning("VK photos.get error (album=%s): %s", album_id, data["error"])
            return []
        items = data.get("response", {}).get("items", []) or []
    except Exception as e:
        logger.warning("VK photos.get упал (album=%s): %s", album_id, e)
        return []

    photos: list[dict] = []
    for p in items:
        pid = p.get("id")
        own = p.get("owner_id") or owner_id
        if not pid:
            continue
        photos.append({
            "id": int(pid),
            "owner_id": int(own),
            "attachment_ref": f"photo{int(own)}_{int(pid)}",
        })
    with _cache_lock:
        _photos_cache[cache_key] = {"ts": now, "photos": photos}
    return photos


# ──────────────────────────────────────────────────────────────────────────────
# Детекция запроса меню → выбор альбома
# ──────────────────────────────────────────────────────────────────────────────
# Триггеры запроса меню (kitchen / bar / generic)
_MENU_KEYWORDS = (
    "меню", "menu", "что у вас поесть", "что у вас покушать", "что покушать",
    "что попить", "что выпить", "карту бара", "барную карту", "бар-карту",
    "что в меню", "поесть", "пожрать", "что по бару", "что по еде",
    "настойк", "коктейл", "что есть выпить", "покажи бар", "покажи кухню",
    "что у вас в баре", "что у вас на кухне", "ассортимент",
)
_KITCHEN_KEYWORDS = (
    "кухн", "поесть", "покушат", "пожрат", "еда", "блюд", "чебурек", "пельмен",
    "борщ", "суп", "оливье", "селёдк", "селедк", "горяч",
)
_BAR_KEYWORDS = (
    "бар", "настойк", "коктейл", "выпить", "пиво", "виски", "ром", "джин",
    "водк", "лимонад", "напитк",
)


def is_menu_query(text: str) -> bool:
    """Похоже ли сообщение на просьбу прислать меню."""
    if not text:
        return False
    low = text.lower()
    return any(kw in low for kw in _MENU_KEYWORDS)


def detect_menu_kind(text: str) -> str:
    """Определяет тип меню по запросу: 'kitchen' | 'bar' | 'all'."""
    low = (text or "").lower()
    is_kitchen = any(kw in low for kw in _KITCHEN_KEYWORDS)
    is_bar = any(kw in low for kw in _BAR_KEYWORDS)
    if is_kitchen and not is_bar:
        return "kitchen"
    if is_bar and not is_kitchen:
        return "bar"
    return "all"


def _match_album(title: str, kind: str) -> bool:
    """Подходит ли альбом под запрашиваемый тип меню."""
    t = (title or "").lower()
    if "меню" not in t and "menu" not in t and "карт" not in t:
        return False
    if kind == "kitchen":
        return any(k in t for k in ("кухн", "еда", "food", "блюд", "kitchen"))
    if kind == "bar":
        return any(k in t for k in ("бар", "напит", "bar", "drink", "коктейл", "настойк"))
    return True


def find_menu_attachments(text: str, max_attachments: int = 6) -> tuple[str, str]:
    """Возвращает (text, attachments_csv) с фото из подходящих альбомов меню."""
    kind = detect_menu_kind(text)
    albums = _fetch_albums()
    if not albums:
        return "", ""

    # 1) Точный матч (kitchen / bar)
    chosen_albums = [a for a in albums if _match_album(a["title"], kind)]
    # 2) Если не нашли — берём все «меню»-альбомы
    if not chosen_albums and kind != "all":
        chosen_albums = [a for a in albums if _match_album(a["title"], "all")]
    if not chosen_albums:
        return "", ""

    refs: list[str] = []
    used_titles: list[str] = []
    for album in chosen_albums:
        if len(refs) >= max_attachments:
            break
        photos = _fetch_album_photos(album["id"], album["owner_id"], count=_MAX_PHOTOS_PER_ALBUM)
        for p in photos:
            refs.append(p["attachment_ref"])
            if len(refs) >= max_attachments:
                break
        if photos:
            used_titles.append(album["title"])

    if not refs:
        return "", ""

    if kind == "kitchen":
        prefix = "Лови меню кухни 🍽 — что у нас вкусного:"
    elif kind == "bar":
        prefix = "Вот барная карта 🥃 — настойки, коктейли и всё к ним:"
    else:
        prefix = "Лови меню — кухня и бар в одном:"

    return prefix, ",".join(refs[:_MAX_SEND])


# ──────────────────────────────────────────────────────────────────────────────
# Товары сообщества (market.get) — пока не использую, оставлено на будущее
# ──────────────────────────────────────────────────────────────────────────────
def fetch_market_items(force: bool = False, count: int = 50) -> list[dict]:
    """Возвращает список товаров сообщества (market.get)."""
    now = time.time()
    with _cache_lock:
        cached = _market_cache.get("items") or []
        if not force and (now - float(_market_cache.get("ts", 0)) < _CACHE_TTL) and cached:
            return cached  # type: ignore[return-value]

    token = _get_token()
    gid = _resolve_group_id()
    if not token or not gid:
        return []

    try:
        r = requests.get(
            f"{_VK_API}/market.get",
            params={
                "access_token": token,
                "v": _VK_VERSION,
                "owner_id": -gid,
                "count": count,
            },
            timeout=10,
        )
        data = r.json()
        if "error" in data:
            logger.warning("VK market.get error: %s", data["error"])
            return []
        items = data.get("response", {}).get("items", []) or []
    except Exception as e:
        logger.warning("VK market.get упал: %s", e)
        return []

    parsed: list[dict] = []
    for it in items:
        iid = it.get("id")
        own = it.get("owner_id") or -gid
        if not iid:
            continue
        parsed.append({
            "id": int(iid),
            "owner_id": int(own),
            "title": (it.get("title") or "").strip(),
            "description": (it.get("description") or "").strip(),
            "price_text": (it.get("price") or {}).get("text", ""),
            "attachment_ref": f"market{int(own)}_{int(iid)}",
        })
    with _cache_lock:
        _market_cache["ts"] = now
        _market_cache["items"] = parsed
    logger.info("VK media: загружено %d товаров", len(parsed))
    return parsed
