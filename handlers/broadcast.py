# handlers/broadcast.py
"""
Система рассылок для BOSS.
Поддерживает: текст, фото, видео, документы, GIF, голос, аудио.
Можно прикреплять инлайн-кнопки (URL) к сообщениям.
Доступ: только BOSS_ID.
"""
import logging
import threading
import time
from telebot import types
from telebot.apihelper import ApiTelegramException
import core.database as database
from core.config import BOSS_IDS
from datetime import datetime
import pytz

logger = logging.getLogger("broadcast")


def _is_boss(user_id: int) -> bool:
    """Проверяет, является ли пользователь боссом."""
    return user_id in (BOSS_IDS or [])


def register_broadcast_handlers(bot):
    """Регистрирует обработчики рассылок (только BOSS)."""

    # Состояния создания рассылки {user_id: {...}}
    broadcast_states: dict = {}

    # ─────────── Команда /broadcast ───────────

    @bot.message_handler(commands=['broadcast'])
    def cmd_broadcast(message):
        if not _is_boss(message.from_user.id):
            return
        _show_broadcast_start(bot, message.chat.id)

    # ─────────── Callback-роутер ───────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('broadcast_'))
    def on_broadcast_callback(call):
        uid = call.from_user.id
        if not _is_boss(uid):
            bot.answer_callback_query(call.id, "⛔ Только для босса")
            return

        action = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        # ── Отмена ──
        if action == "broadcast_cancel":
            broadcast_states.pop(uid, None)
            bot.edit_message_text("❌ Рассылка отменена.", chat_id, msg_id)
            return

        # ── Выбор типа ──
        if action == "broadcast_text":
            broadcast_states[uid] = {"type": "text", "step": "waiting_content"}
            bot.edit_message_text(
                "📝 <b>Текстовая рассылка</b>\n\n"
                "Отправь мне текст сообщения.\n"
                "Поддерживается HTML-разметка:\n"
                "• <code>&lt;b&gt;жирный&lt;/b&gt;</code>\n"
                "• <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
                "• <code>&lt;a href=\"url\"&gt;ссылка&lt;/a&gt;</code>\n\n"
                "Для отмены → /cancel_broadcast",
                chat_id, msg_id, parse_mode="HTML"
            )
            return

        if action == "broadcast_media":
            broadcast_states[uid] = {"type": "media", "step": "waiting_media"}
            bot.edit_message_text(
                "📷 <b>Рассылка с медиа</b>\n\n"
                "Отправь фото, видео, GIF, документ, голосовое или аудио.\n\n"
                "Для отмены → /cancel_broadcast",
                chat_id, msg_id, parse_mode="HTML"
            )
            return

        # ── Добавить кнопку ──
        if action == "broadcast_add_button":
            state = broadcast_states.get(uid)
            if not state:
                bot.answer_callback_query(call.id, "❌ Рассылка не найдена")
                return
            state["step"] = "waiting_button_text"
            bot.edit_message_text(
                "🔘 <b>Добавление кнопки</b>\n\n"
                "Отправь <b>текст кнопки</b> (до 40 символов).\n\n"
                "Для отмены → /cancel_broadcast",
                chat_id, msg_id, parse_mode="HTML"
            )
            return

        # ── Удалить последнюю кнопку ──
        if action == "broadcast_remove_button":
            state = broadcast_states.get(uid)
            if state and state.get("buttons"):
                removed = state["buttons"].pop()
                bot.answer_callback_query(call.id, f"🗑 Кнопка «{removed['text']}» удалена")
                _show_preview(bot, uid, state, chat_id)
            else:
                bot.answer_callback_query(call.id, "Нет кнопок для удаления")
            return

        # ── Тестовая отправка (себе) ──
        if action == "broadcast_test":
            state = broadcast_states.get(uid)
            if not state:
                bot.answer_callback_query(call.id, "❌ Рассылка не найдена")
                return
            ok = _send_to_user(bot, uid, state)
            bot.answer_callback_query(
                call.id,
                "✅ Тестовое сообщение отправлено!" if ok else "❌ Ошибка отправки"
            )
            return

        # ── Отправить ВСЕМ — подтверждение ──
        if action == "broadcast_send_all":
            state = broadcast_states.get(uid)
            if not state:
                bot.answer_callback_query(call.id, "❌ Рассылка не найдена")
                return

            users = database.get_all_users_for_broadcast()
            count = len(users) if users else 0

            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("✅ Да, отправить!", callback_data="broadcast_confirm"),
                types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel"),
            )

            bot.edit_message_text(
                f"⚠️ <b>Подтверди рассылку</b>\n\n"
                f"Сообщение получат <b>{count}</b> пользователей.\n\n"
                f"Уверен?",
                chat_id, msg_id, parse_mode="HTML", reply_markup=kb
            )
            return

        # ── Подтверждение — запуск ──
        if action == "broadcast_confirm":
            state = broadcast_states.get(uid)
            if not state:
                bot.answer_callback_query(call.id, "❌ Рассылка не найдена")
                return

            bot.edit_message_text(
                "🚀 <b>Рассылка запущена…</b>\n\nОжидайте статус.",
                chat_id, msg_id, parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "🚀 Поехали!")

            threading.Thread(
                target=_run_broadcast,
                args=(bot, uid, state, chat_id, msg_id),
                daemon=True,
            ).start()

            # Убираем состояние чтобы не ловить новые сообщения
            broadcast_states.pop(uid, None)
            return

        # ── Статистика рассылок ──
        if action == "broadcast_stats":
            stats = database.get_broadcast_statistics()
            if stats:
                text = (
                    "📊 <b>Статистика базы</b>\n\n"
                    f"👥 Всего зарегистрировано: <b>{stats['total']}</b>\n"
                    f"✅ Активных (получат рассылку): <b>{stats['active']}</b>\n"
                    f"🚫 Заблокировали бота: <b>{stats['blocked']}</b>\n"
                    f"🆕 Новых за 30 дней: <b>{stats['recent_30d']}</b>\n"
                )
            else:
                text = "❌ Не удалось получить статистику."

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_menu_broadcasts"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=kb)
            return

        # ── Создать рассылку (из админки) ──
        if action == "broadcast_create":
            _show_broadcast_start(bot, chat_id, edit_msg_id=msg_id)
            return

    # ─────────── Обработчик контента ───────────

    @bot.message_handler(
        func=lambda m: m.from_user.id in broadcast_states and _is_boss(m.from_user.id),
        content_types=[
            'text', 'photo', 'video', 'document',
            'animation', 'voice', 'audio'
        ]
    )
    def on_broadcast_content(message):
        uid = message.from_user.id
        state = broadcast_states.get(uid)
        if not state:
            return

        # Отмена
        if message.content_type == 'text' and message.text == "/cancel_broadcast":
            broadcast_states.pop(uid, None)
            bot.send_message(message.chat.id, "❌ Рассылка отменена.")
            return

        step = state["step"]

        # ── Ожидаем текст рассылки ──
        if step == "waiting_content" and state["type"] == "text":
            if message.content_type != 'text':
                bot.send_message(message.chat.id, "⚠️ Ожидаю текст. Отправь текстовое сообщение.")
                return
            state["content"] = message.text
            state["buttons"] = state.get("buttons", [])
            _show_preview(bot, uid, state, message.chat.id)
            return

        # ── Ожидаем медиа ──
        if step == "waiting_media" and state["type"] == "media":
            media = _extract_media(message)
            if not media:
                bot.send_message(message.chat.id, "⚠️ Неподдерживаемый тип. Отправь фото, видео, GIF, документ, голосовое или аудио.")
                return
            state["media"] = media
            # Если у медиа уже есть подпись — используем её
            if message.caption:
                state["content"] = message.caption
                state["buttons"] = state.get("buttons", [])
                _show_preview(bot, uid, state, message.chat.id)
            else:
                state["step"] = "waiting_caption"
                bot.send_message(
                    message.chat.id,
                    "📝 Отправь <b>подпись</b> к медиа или /skip_caption чтобы оставить без подписи.",
                    parse_mode="HTML"
                )
            return

        # ── Ожидаем подпись к медиа ──
        if step == "waiting_caption" and state["type"] == "media":
            if message.content_type != 'text':
                bot.send_message(message.chat.id, "⚠️ Ожидаю текст подписи.")
                return
            if message.text == "/skip_caption":
                state["content"] = ""
            else:
                state["content"] = message.text
            state["buttons"] = state.get("buttons", [])
            _show_preview(bot, uid, state, message.chat.id)
            return

        # ── Ожидаем текст кнопки ──
        if step == "waiting_button_text":
            if message.content_type != 'text':
                bot.send_message(message.chat.id, "⚠️ Ожидаю текст кнопки.")
                return
            btn_text = message.text.strip()[:40]
            state["_pending_button_text"] = btn_text
            state["step"] = "waiting_button_url"
            bot.send_message(
                message.chat.id,
                f"🔗 Теперь отправь <b>URL</b> для кнопки «{btn_text}».",
                parse_mode="HTML"
            )
            return

        # ── Ожидаем URL кнопки ──
        if step == "waiting_button_url":
            if message.content_type != 'text':
                bot.send_message(message.chat.id, "⚠️ Ожидаю ссылку (URL).")
                return
            url = message.text.strip()
            if not url.startswith(("http://", "https://")):
                bot.send_message(message.chat.id, "⚠️ URL должен начинаться с http:// или https://")
                return
            btn_text = state.pop("_pending_button_text", "Кнопка")
            state.setdefault("buttons", []).append({"text": btn_text, "url": url})
            _show_preview(bot, uid, state, message.chat.id)
            return

    # ─────────── Вспомогательные функции ───────────

    def _show_broadcast_start(bot_inst, chat_id, edit_msg_id=None):
        """Показывает стартовое меню создания рассылки."""
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(
            types.InlineKeyboardButton("📝 Текст", callback_data="broadcast_text"),
            types.InlineKeyboardButton("📷 Медиа", callback_data="broadcast_media"),
        )
        kb.row(
            types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel"),
        )

        text = (
            "📢 <b>Создание рассылки</b>\n\n"
            "Выбери тип сообщения:"
        )

        if edit_msg_id:
            bot_inst.edit_message_text(text, chat_id, edit_msg_id, parse_mode="HTML", reply_markup=kb)
        else:
            bot_inst.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)

    def _show_preview(bot_inst, uid, state, chat_id):
        """Показывает превью рассылки с кнопками управления."""
        state["step"] = "preview"

        # Кнопки управления
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(
            types.InlineKeyboardButton("🧪 Тест (мне)", callback_data="broadcast_test"),
            types.InlineKeyboardButton("📢 Отправить ВСЕМ", callback_data="broadcast_send_all"),
        )

        # Кнопки к сообщению
        btn_count = len(state.get("buttons", []))
        if btn_count < 3:
            kb.row(types.InlineKeyboardButton(f"🔘 Добавить кнопку ({btn_count}/3)", callback_data="broadcast_add_button"))
        if btn_count > 0:
            kb.row(types.InlineKeyboardButton("🗑 Удалить последнюю кнопку", callback_data="broadcast_remove_button"))

        kb.row(types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel"))

        # Формируем текст превью
        preview = "✅ <b>Рассылка готова!</b>\n\n"

        if state["type"] == "text":
            preview += f"<b>Текст:</b>\n{state['content'][:500]}\n\n"
        else:
            media_type_names = {
                "photo": "📷 Фото", "video": "🎬 Видео", "document": "📎 Документ",
                "animation": "🎞 GIF", "voice": "🎤 Голосовое", "audio": "🎵 Аудио",
            }
            media_name = media_type_names.get(state["media"]["type"], "📎 Медиа")
            preview += f"<b>Тип:</b> {media_name}\n"
            if state.get("content"):
                preview += f"<b>Подпись:</b> {state['content'][:200]}\n\n"

        if state.get("buttons"):
            preview += "<b>Кнопки:</b>\n"
            for i, btn in enumerate(state["buttons"], 1):
                preview += f"  {i}. [{btn['text']}] → {btn['url'][:50]}\n"
            preview += "\n"

        preview += "Выбери действие 👇"

        bot_inst.send_message(chat_id, preview, parse_mode="HTML", reply_markup=kb)


# ═══════════════════════════════════════════
# Функции вне register_broadcast_handlers
# (доступны из потоков)
# ═══════════════════════════════════════════


def _extract_media(message) -> dict | None:
    """Извлекает медиа из сообщения."""
    if message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id}
    if message.video:
        return {"type": "video", "file_id": message.video.file_id}
    if message.animation:
        return {"type": "animation", "file_id": message.animation.file_id}
    if message.document:
        return {"type": "document", "file_id": message.document.file_id}
    if message.voice:
        return {"type": "voice", "file_id": message.voice.file_id}
    if message.audio:
        return {"type": "audio", "file_id": message.audio.file_id}
    return None


def _build_inline_keyboard(buttons: list[dict]) -> types.InlineKeyboardMarkup | None:
    """Строит инлайн-клавиатуру из списка кнопок."""
    if not buttons:
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        kb.add(types.InlineKeyboardButton(text=btn["text"], url=btn["url"]))
    return kb


def _send_to_user(bot, user_id: int, state: dict) -> bool:
    """Отправляет рассылку одному пользователю. Возвращает True при успехе."""
    try:
        markup = _build_inline_keyboard(state.get("buttons", []))
        caption = state.get("content") or None

        if state["type"] == "text":
            bot.send_message(user_id, state["content"], parse_mode="HTML", reply_markup=markup)
        else:
            media = state["media"]
            fid = media["file_id"]
            t = media["type"]

            sender = {
                "photo": bot.send_photo,
                "video": bot.send_video,
                "animation": bot.send_animation,
                "document": bot.send_document,
                "voice": bot.send_voice,
                "audio": bot.send_audio,
            }.get(t)

            if sender:
                sender(user_id, fid, caption=caption, parse_mode="HTML", reply_markup=markup)
            else:
                return False
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
        return False


def _run_broadcast(bot, boss_id: int, state: dict, status_chat: int, status_msg: int):
    """Запускает массовую рассылку в отдельном потоке."""
    users = database.get_all_users_for_broadcast()
    if not users:
        bot.edit_message_text("❌ Нет пользователей для рассылки.", status_chat, status_msg)
        return

    total = len(users)
    sent = 0
    failed = 0
    blocked = 0

    moscow = pytz.timezone("Europe/Moscow")
    start_time = datetime.now(moscow)

    for i, user in enumerate(users):
        uid = user.get("user_id")
        if not uid:
            continue

        try:
            ok = _send_to_user(bot, uid, state)
            if ok:
                sent += 1
            else:
                failed += 1
        except ApiTelegramException as e:
            if e.error_code == 403:
                blocked += 1
                try:
                    database.mark_user_blocked(uid)
                except Exception:
                    pass
            elif e.error_code == 429:
                # Too Many Requests — ждём
                retry_after = 1
                try:
                    retry_after = int(e.result_json.get("parameters", {}).get("retry_after", 1))
                except Exception:
                    pass
                logger.warning(f"429 Too Many Requests, ждём {retry_after}s")
                time.sleep(retry_after)
                # Повторная попытка
                try:
                    _send_to_user(bot, uid, state)
                    sent += 1
                except Exception:
                    failed += 1
            else:
                failed += 1
                logger.error(f"Telegram ошибка {e.error_code} для {uid}: {e}")
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка отправки {uid}: {e}")

        # Обновление статуса каждые 15 сообщений
        if (i + 1) % 15 == 0:
            pct = round((i + 1) / total * 100, 1)
            try:
                bot.edit_message_text(
                    f"📤 <b>Рассылка…</b> {i + 1}/{total} ({pct}%)\n\n"
                    f"✅ Отправлено: {sent}\n"
                    f"❌ Ошибок: {failed}\n"
                    f"🚫 Заблокировали: {blocked}",
                    status_chat, status_msg, parse_mode="HTML"
                )
            except Exception:
                pass

        # Задержка между отправками (~20 msg/sec)
        time.sleep(0.05)

    # ── Финальный отчёт ──
    elapsed = (datetime.now(moscow) - start_time).total_seconds()
    success_rate = round(sent / total * 100, 1) if total else 0

    report = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 <b>Итоги:</b>\n"
        f"├ Всего пользователей: <b>{total}</b>\n"
        f"├ ✅ Доставлено: <b>{sent}</b>\n"
        f"├ ❌ Ошибок: <b>{failed}</b>\n"
        f"├ 🚫 Заблокировали: <b>{blocked}</b>\n"
        f"├ 🎯 Доставляемость: <b>{success_rate}%</b>\n"
        f"└ ⏱ Время: <b>{round(elapsed, 1)} сек.</b>\n\n"
        f"📅 {start_time.strftime('%d.%m.%Y %H:%M')} МСК"
    )

    try:
        bot.edit_message_text(report, status_chat, status_msg, parse_mode="HTML")
    except Exception:
        bot.send_message(boss_id, report, parse_mode="HTML")

    logger.info(
        f"Рассылка завершена: sent={sent}/{total}, failed={failed}, blocked={blocked}, "
        f"time={round(elapsed, 1)}s"
    )
