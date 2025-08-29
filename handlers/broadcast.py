# handlers/broadcast.py
import logging
import threading
import time
from typing import List, Dict, Optional
from telebot import types
from telebot.apihelper import ApiTelegramException
import core.database as database
from datetime import datetime
import pytz

def register_broadcast_handlers(bot):
    """
    Регистрирует обработчики для системы рассылок
    """
    
    # Состояния для создания рассылки
    broadcast_states = {}
    
    @bot.message_handler(commands=['broadcast'])
    def handle_broadcast_command(message):
        """
        Команда для запуска создания рассылки (только для админов)
        """
        if not database.is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ У вас нет прав для создания рассылок")
            return
        
        # Создаем клавиатуру для выбора типа рассылки
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("📝 Текстовая рассылка", callback_data="broadcast_text"),
            types.InlineKeyboardButton("📷 Рассылка с медиа", callback_data="broadcast_media")
        )
        keyboard.row(
            types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
        )
        
        text = "📢 *Система рассылок*\n\n"
        text += "Выберите тип рассылки:"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=keyboard)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('broadcast_'))
    def handle_broadcast_callbacks(call):
        """
        Обработчик callback'ов для системы рассылок
        """
        user_id = call.from_user.id
        
        if not database.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ У вас нет прав")
            return
        
        if call.data == "broadcast_cancel":
            # Отмена создания рассылки
            if user_id in broadcast_states:
                del broadcast_states[user_id]
            bot.edit_message_text(
                "❌ Создание рассылки отменено",
                call.message.chat.id,
                call.message.message_id
            )
            return
        
        elif call.data == "broadcast_text":
            # Начинаем создание текстовой рассылки
            broadcast_states[user_id] = {
                'type': 'text',
                'step': 'waiting_content',
                'message_id': call.message.message_id
            }
            
            text = "📝 *Создание текстовой рассылки*\n\n"
            text += "Отправьте мне текст сообщения для рассылки.\n"
            text += "Вы можете использовать Markdown форматирование:\n"
            text += "• **жирный текст**\n"
            text += "• *курсив*\n"
            text += "• `код`\n"
            text += "• [ссылка](http://example.com)\n\n"
            text += "Для отмены отправьте /cancel"
            
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        elif call.data == "broadcast_media":
            # Начинаем создание рассылки с медиа
            broadcast_states[user_id] = {
                'type': 'media',
                'step': 'waiting_media',
                'message_id': call.message.message_id
            }
            
            text = "📷 *Создание рассылки с медиа*\n\n"
            text += "Отправьте мне изображение, видео или другой медиафайл.\n"
            text += "После этого вы сможете добавить подпись к сообщению.\n\n"
            text += "Для отмены отправьте /cancel"
            
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        elif call.data == "broadcast_test":
            # Тестовая отправка
            if user_id not in broadcast_states:
                bot.answer_callback_query(call.id, "❌ Данные рассылки не найдены")
                return
            
            state = broadcast_states[user_id]
            success = send_test_broadcast(bot, user_id, state)
            
            if success:
                bot.answer_callback_query(call.id, "✅ Тестовое сообщение отправлено!")
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка отправки тестового сообщения")
        
        elif call.data == "broadcast_send_all":
            # Отправка всем пользователям
            if user_id not in broadcast_states:
                bot.answer_callback_query(call.id, "❌ Данные рассылки не найдены")
                return
            
            state = broadcast_states[user_id]
            
            # Показываем подтверждение
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast_confirm_all"),
                types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
            )
            
            all_users = database.get_all_users_for_broadcast()
            user_count = len(all_users) if all_users else 0
            
            text = f"⚠️ *Подтвердите массовую рассылку*\n\n"
            text += f"Сообщение будет отправлено **{user_count}** пользователям.\n\n"
            text += "Вы уверены?"
            
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
        elif call.data == "broadcast_confirm_all":
            # Подтверждение массовой рассылки
            if user_id not in broadcast_states:
                bot.answer_callback_query(call.id, "❌ Данные рассылки не найдены")
                return
            
            state = broadcast_states[user_id]
            
            # Запускаем рассылку в отдельном потоке
            threading.Thread(
                target=start_mass_broadcast,
                args=(bot, user_id, state, call.message.chat.id, call.message.message_id),
                daemon=True
            ).start()
            
            bot.answer_callback_query(call.id, "🚀 Рассылка запущена!")
    
    @bot.message_handler(func=lambda message: message.from_user.id in broadcast_states)
    def handle_broadcast_content(message):
        """
        Обработчик контента для рассылки
        """
        user_id = message.from_user.id
        
        if message.text == "/cancel":
            # Отмена создания рассылки
            del broadcast_states[user_id]
            bot.send_message(message.chat.id, "❌ Создание рассылки отменено")
            return
        
        state = broadcast_states[user_id]
        
        if state['step'] == 'waiting_content' and state['type'] == 'text':
            # Получили текст для рассылки
            state['content'] = message.text
            state['message_format'] = 'text'
            show_broadcast_preview(bot, user_id, state, message.chat.id)
        
        elif state['step'] == 'waiting_media' and state['type'] == 'media':
            # Получили медиа файл
            media_info = extract_media_info(message)
            if media_info:
                state['media'] = media_info
                state['step'] = 'waiting_caption'
                
                text = "📝 *Добавьте подпись к медиа*\n\n"
                text += "Отправьте текст подписи или отправьте /skip чтобы отправить без подписи.\n"
                text += "Для отмены отправьте /cancel"
                
                bot.send_message(message.chat.id, text, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Неподдерживаемый тип медиа. Попробуйте еще раз.")
        
        elif state['step'] == 'waiting_caption' and state['type'] == 'media':
            # Получили подпись для медиа
            if message.text == "/skip":
                state['content'] = ""
            else:
                state['content'] = message.text
            
            state['message_format'] = 'media'
            show_broadcast_preview(bot, user_id, state, message.chat.id)

def extract_media_info(message):
    """
    Извлекает информацию о медиафайле из сообщения
    """
    if message.photo:
        return {
            'type': 'photo',
            'file_id': message.photo[-1].file_id,  # Берем фото наилучшего качества
            'caption': message.caption
        }
    elif message.video:
        return {
            'type': 'video',
            'file_id': message.video.file_id,
            'caption': message.caption
        }
    elif message.document:
        return {
            'type': 'document',
            'file_id': message.document.file_id,
            'caption': message.caption
        }
    elif message.animation:  # GIF
        return {
            'type': 'animation',
            'file_id': message.animation.file_id,
            'caption': message.caption
        }
    elif message.voice:
        return {
            'type': 'voice',
            'file_id': message.voice.file_id,
            'caption': message.caption
        }
    elif message.audio:
        return {
            'type': 'audio',
            'file_id': message.audio.file_id,
            'caption': message.caption
        }
    
    return None

def show_broadcast_preview(bot, user_id, state, chat_id):
    """
    Показывает превью рассылки с кнопками для отправки
    """
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🧪 ТЕСТ (мне)", callback_data="broadcast_test"),
        types.InlineKeyboardButton("📢 ВСЕМ", callback_data="broadcast_send_all")
    )
    keyboard.row(
        types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
    )
    
    preview_text = "✅ *Рассылка готова!*\n\n"
    preview_text += "**Превью сообщения:**\n"
    preview_text += "─────────────────────\n"
    
    if state['message_format'] == 'text':
        preview_text += f"{state['content']}\n"
    else:
        preview_text += f"📎 Медиафайл ({state['media']['type']})\n"
        if state['content']:
            preview_text += f"Подпись: {state['content']}\n"
    
    preview_text += "─────────────────────\n\n"
    preview_text += "Выберите действие:"
    
    # Отправляем превью
    if state['message_format'] == 'media':
        # Если это медиа, отправляем медиа с превью текстом как подпись
        send_media_message(bot, chat_id, state['media'], preview_text, keyboard)
    else:
        # Обычное текстовое сообщение
        bot.send_message(chat_id, preview_text, parse_mode="Markdown", reply_markup=keyboard)

def send_media_message(bot, chat_id, media_info, caption, keyboard=None):
    """
    Отправляет медиа сообщение
    """
    try:
        if media_info['type'] == 'photo':
            bot.send_photo(
                chat_id, 
                media_info['file_id'], 
                caption=caption, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif media_info['type'] == 'video':
            bot.send_video(
                chat_id, 
                media_info['file_id'], 
                caption=caption, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif media_info['type'] == 'document':
            bot.send_document(
                chat_id, 
                media_info['file_id'], 
                caption=caption, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif media_info['type'] == 'animation':
            bot.send_animation(
                chat_id, 
                media_info['file_id'], 
                caption=caption, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif media_info['type'] == 'voice':
            bot.send_voice(
                chat_id, 
                media_info['file_id'], 
                caption=caption, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif media_info['type'] == 'audio':
            bot.send_audio(
                chat_id, 
                media_info['file_id'], 
                caption=caption, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        logging.error(f"Ошибка отправки медиа сообщения: {e}")
        bot.send_message(chat_id, f"❌ Ошибка отправки медиа: {str(e)}")

def send_test_broadcast(bot, admin_id, state):
    """
    Отправляет тестовое сообщение администратору
    """
    try:
        if state['message_format'] == 'text':
            bot.send_message(admin_id, state['content'], parse_mode="Markdown")
        else:
            send_broadcast_media_to_user(bot, admin_id, state)
        return True
    except Exception as e:
        logging.error(f"Ошибка отправки тестового сообщения: {e}")
        return False

def send_broadcast_media_to_user(bot, user_id, state):
    """
    Отправляет медиа сообщение пользователю
    """
    media_info = state['media']
    caption = state['content'] if state['content'] else None
    
    if media_info['type'] == 'photo':
        bot.send_photo(user_id, media_info['file_id'], caption=caption, parse_mode="Markdown")
    elif media_info['type'] == 'video':
        bot.send_video(user_id, media_info['file_id'], caption=caption, parse_mode="Markdown")
    elif media_info['type'] == 'document':
        bot.send_document(user_id, media_info['file_id'], caption=caption, parse_mode="Markdown")
    elif media_info['type'] == 'animation':
        bot.send_animation(user_id, media_info['file_id'], caption=caption, parse_mode="Markdown")
    elif media_info['type'] == 'voice':
        bot.send_voice(user_id, media_info['file_id'], caption=caption, parse_mode="Markdown")
    elif media_info['type'] == 'audio':
        bot.send_audio(user_id, media_info['file_id'], caption=caption, parse_mode="Markdown")

def start_mass_broadcast(bot, admin_id, state, status_chat_id, status_message_id):
    """
    Запускает массовую рассылку в отдельном потоке
    """
    try:
        # Получаем всех пользователей
        all_users = database.get_all_users_for_broadcast()
        
        if not all_users:
            bot.edit_message_text(
                "❌ Не найдено пользователей для рассылки",
                status_chat_id,
                status_message_id
            )
            return
        
        total_users = len(all_users)
        sent_count = 0
        failed_count = 0
        blocked_count = 0
        
        # Обновляем статус начала рассылки
        status_text = f"🚀 *Рассылка запущена*\n\n"
        status_text += f"Всего пользователей: {total_users}\n"
        status_text += f"Отправлено: {sent_count}\n"
        status_text += f"Ошибок: {failed_count}\n"
        status_text += f"Заблокировали бота: {blocked_count}"
        
        bot.edit_message_text(
            status_text,
            status_chat_id,
            status_message_id,
            parse_mode="Markdown"
        )
        
        # Отправляем сообщения с задержкой (чтобы не попасть в лимиты Telegram)
        for i, user in enumerate(all_users):
            try:
                user_id = user.get('user_id')
                if not user_id:
                    continue
                
                # Отправляем сообщение
                if state['message_format'] == 'text':
                    bot.send_message(user_id, state['content'], parse_mode="Markdown")
                else:
                    send_broadcast_media_to_user(bot, user_id, state)
                
                sent_count += 1
                
                # Логируем успешную отправку
                logging.info(f"Рассылка отправлена пользователю {user_id}")
                
            except ApiTelegramException as e:
                if e.error_code == 403:  # Пользователь заблокировал бота
                    blocked_count += 1
                    logging.info(f"Пользователь {user_id} заблокировал бота")
                    # Помечаем пользователя как заблокировавшего бота
                    database.mark_user_blocked(user_id)
                else:
                    failed_count += 1
                    logging.error(f"Ошибка отправки пользователю {user_id}: {e}")
            
            except Exception as e:
                failed_count += 1
                logging.error(f"Неожиданная ошибка отправки пользователю {user_id}: {e}")
            
            # Обновляем статус каждые 10 отправленных сообщений
            if (i + 1) % 10 == 0 or i == total_users - 1:
                status_text = f"📊 *Статус рассылки*\n\n"
                status_text += f"Всего пользователей: {total_users}\n"
                status_text += f"✅ Отправлено: {sent_count}\n"
                status_text += f"❌ Ошибок: {failed_count}\n"
                status_text += f"🚫 Заблокировали бота: {blocked_count}\n"
                status_text += f"⏳ Прогресс: {i + 1}/{total_users} ({round((i + 1) / total_users * 100, 1)}%)"
                
                try:
                    bot.edit_message_text(
                        status_text,
                        status_chat_id,
                        status_message_id,
                        parse_mode="Markdown"
                    )
                except:
                    pass  # Игнорируем ошибки обновления статуса
            
            # Задержка между отправками (30 сообщений в секунду максимум для Telegram)
            time.sleep(0.05)
        
        # Финальный отчет
        status_text = f"✅ *Рассылка завершена!*\n\n"
        status_text += f"📊 **Итоговая статистика:**\n"
        status_text += f"• Всего пользователей: {total_users}\n"
        status_text += f"• ✅ Успешно отправлено: {sent_count}\n"
        status_text += f"• ❌ Ошибок отправки: {failed_count}\n"
        status_text += f"• 🚫 Заблокировали бота: {blocked_count}\n\n"
        
        success_rate = round((sent_count / total_users) * 100, 1) if total_users > 0 else 0
        status_text += f"🎯 Процент успешной доставки: {success_rate}%"
        
        # Логируем завершение рассылки
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        logging.info(f"Рассылка завершена в {current_time}. "
                    f"Отправлено: {sent_count}/{total_users}. "
                    f"Ошибок: {failed_count}. Заблокировали: {blocked_count}")
        
        # Обновляем статус
        bot.edit_message_text(
            status_text,
            status_chat_id,
            status_message_id,
            parse_mode="Markdown"
        )
        
        # Отправляем администратору уведомление о завершении
        notification_text = f"📢 *Рассылка завершена!*\n\n"
        notification_text += f"Успешно доставлено {sent_count} из {total_users} сообщений"
        
        bot.send_message(admin_id, notification_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Критическая ошибка в массовой рассылке: {e}")
        
        error_text = f"❌ *Ошибка рассылки*\n\n"
        error_text += f"Произошла критическая ошибка: {str(e)}\n\n"
        error_text += f"Отправлено сообщений: {sent_count}"
        
        try:
            bot.edit_message_text(
                error_text,
                status_chat_id,
                status_message_id,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(admin_id, error_text, parse_mode="Markdown")
