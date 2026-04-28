# /handlers/utils.py
"""
Вспомогательные утилиты для бота.
"""
import logging
import re


def shorten_name(full_name: str) -> str:
    """Превращает 'Иван Смирнов' в 'Иван С.'"""
    parts = full_name.split()
    if len(parts) > 1:
        return f"{parts[0]} {parts[1][0]}."
    return full_name


# Символы, которые ломают Markdown-парсер Telegram.
# Используется для ЭКРАНИРОВАНИЯ user-input при отправке с parse_mode="Markdown".
_MD_SPECIALS_RE = re.compile(r'([_*`\[\]])')


def escape_markdown(text) -> str:
    """Экранирует спецсимволы Markdown (legacy) — `_ * ` [ ]`.

    Применяется к динамическим данным от пользователя (имена, username, payload),
    которые встраиваются в шаблон с parse_mode="Markdown".
    """
    if text is None:
        return ''
    return _MD_SPECIALS_RE.sub(r'\\\1', str(text))


def safe_send_message(bot, chat_id, text, **kwargs):
    """Безопасная отправка сообщения с graceful fallback на plain text.

    Если Telegram отклонил сообщение из-за ошибки парсинга Markdown/HTML
    (например, в имени гостя «_test_» или непарная *), повторяет отправку
    без parse_mode и без reply_markup. Никогда не бросает исключение наружу.

    Возвращает Message при успехе или None при полном провале.
    """
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        msg = str(e).lower()
        if 'parse' in msg or "can't parse entities" in msg or 'bad request' in msg:
            try:
                kwargs.pop('parse_mode', None)
                return bot.send_message(chat_id, text, **kwargs)
            except Exception as e2:
                logging.error(f"safe_send_message: fallback тоже упал для chat={chat_id}: {e2}")
                return None
        logging.error(f"safe_send_message: ошибка отправки в chat={chat_id}: {e}")
        return None
