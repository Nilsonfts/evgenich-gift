# /handlers/admin_content.py
"""
Команды для управления динамическим контентом
Только для боссов/админов
AI System v3.0
"""

import logging
from telebot import TeleBot, types
from core.config import BOSS_IDS, ALL_ADMINS
from ai.dynamic_content import dynamic_content
from ai.user_memory import user_memory

logger = logging.getLogger("evgenich_bot")


def is_boss(user_id: int) -> bool:
    """Проверить является ли пользователь боссом"""
    return user_id in BOSS_IDS


def is_admin(user_id: int) -> bool:
    """Проверить является ли пользователь админом"""
    return user_id in ALL_ADMINS or user_id in BOSS_IDS


def register_content_handlers(bot: TeleBot):
    """Регистрация обработчиков для управления контентом"""
    
    # ==================== АКЦИИ ====================
    
    @bot.message_handler(commands=['add_promo'])
    def add_promotion_cmd(message: types.Message):
        """
        Добавить акцию
        Формат: /add_promo Название | Описание | Дата окончания (опционально)
        """
        user_id = message.from_user.id
        
        if not is_boss(user_id):
            bot.reply_to(message, "⛔ Эта команда только для боссов!")
            return
        
        try:
            text = message.text.replace('/add_promo', '').strip()
            
            if not text or '|' not in text:
                bot.reply_to(message, 
                    "📝 *Формат команды:*\n"
                    "`/add_promo Название | Описание | Дата окончания`\n\n"
                    "*Примеры:*\n"
                    "`/add_promo Happy Hour | Скидка 20% на настойки до 18:00 | 2026-02-01`\n"
                    "`/add_promo Вечер караоке | Бесплатное караоке для всех!`\n\n"
                    "Дата окончания опциональна (формат: YYYY-MM-DD)",
                    parse_mode="Markdown"
                )
                return
            
            parts = [p.strip() for p in text.split('|')]
            
            if len(parts) < 2:
                bot.reply_to(message, "❌ Нужно указать хотя бы название и описание!")
                return
            
            title = parts[0]
            description = parts[1]
            valid_until = parts[2] if len(parts) > 2 else None
            
            promo = dynamic_content.add_promotion(title, description, valid_until)
            
            response = (
                f"✅ *Акция добавлена!*\n\n"
                f"📌 *{promo['title']}*\n"
                f"📝 {promo['description']}\n"
                f"⏰ До: {promo.get('valid_until') or 'бессрочно'}\n"
                f"🆔 ID: #{promo['id']}"
            )
            bot.reply_to(message, response, parse_mode="Markdown")
            logger.info(f"🎁 Босс {user_id} добавил акцию: {title}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления акции: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")
    
    @bot.message_handler(commands=['list_promos', 'promos'])
    def list_promos_cmd(message: types.Message):
        """Список активных акций"""
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "⛔ Только для админов!")
            return
        
        promos = dynamic_content.get_active_promotions()
        
        if not promos:
            bot.reply_to(message, "📭 Нет активных акций\n\nДобавить: `/add_promo Название | Описание`", parse_mode="Markdown")
            return
        
        text = "🎁 *АКТИВНЫЕ АКЦИИ:*\n\n"
        for p in promos:
            text += f"*#{p['id']}* {p['title']}\n"
            text += f"   📝 {p['description']}\n"
            text += f"   ⏰ До: {p.get('valid_until') or 'бессрочно'}\n\n"
        
        text += "➖➖➖\n"
        text += "Удалить: `/del_promo <id>`\n"
        text += "Добавить: `/add_promo Название | Описание`"
        
        bot.reply_to(message, text, parse_mode="Markdown")
    
    @bot.message_handler(commands=['del_promo'])
    def delete_promo_cmd(message: types.Message):
        """Удалить акцию: /del_promo <id>"""
        user_id = message.from_user.id
        
        if not is_boss(user_id):
            bot.reply_to(message, "⛔ Только для боссов!")
            return
        
        try:
            promo_id = int(message.text.replace('/del_promo', '').strip())
            if dynamic_content.deactivate_promotion(promo_id):
                bot.reply_to(message, f"✅ Акция #{promo_id} удалена")
                logger.info(f"🗑️ Босс {user_id} удалил акцию #{promo_id}")
            else:
                bot.reply_to(message, f"❌ Акция #{promo_id} не найдена")
        except ValueError:
            bot.reply_to(message, "📝 Формат: `/del_promo <id>`\n\nПример: `/del_promo 1`", parse_mode="Markdown")
    
    # ==================== МЕРОПРИЯТИЯ ====================
    
    @bot.message_handler(commands=['add_event'])
    def add_event_cmd(message: types.Message):
        """
        Добавить мероприятие
        Формат: /add_event Название | Описание | Дата | Время
        """
        user_id = message.from_user.id
        
        if not is_boss(user_id):
            bot.reply_to(message, "⛔ Только для боссов!")
            return
        
        try:
            text = message.text.replace('/add_event', '').strip()
            
            if not text or '|' not in text:
                bot.reply_to(message, 
                    "📝 *Формат команды:*\n"
                    "`/add_event Название | Описание | Дата | Время`\n\n"
                    "*Пример:*\n"
                    "`/add_event Караоке-баттл | Призы победителям! | 2026-01-10 | 20:00`\n\n"
                    "Дата в формате: YYYY-MM-DD\n"
                    "Время в формате: HH:MM",
                    parse_mode="Markdown"
                )
                return
            
            parts = [p.strip() for p in text.split('|')]
            
            if len(parts) < 4:
                bot.reply_to(message, "❌ Нужно указать: Название | Описание | Дата | Время")
                return
            
            title, description, date, time = parts[:4]
            
            event = dynamic_content.add_event(title, description, date, time)
            
            response = (
                f"✅ *Мероприятие добавлено!*\n\n"
                f"🎉 *{event['title']}*\n"
                f"📝 {event['description']}\n"
                f"📅 {event['date']} в {event['time']}\n"
                f"🆔 ID: #{event['id']}"
            )
            bot.reply_to(message, response, parse_mode="Markdown")
            logger.info(f"🎉 Босс {user_id} добавил мероприятие: {title}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления мероприятия: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")
    
    @bot.message_handler(commands=['list_events', 'events'])
    def list_events_cmd(message: types.Message):
        """Список мероприятий"""
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "⛔ Только для админов!")
            return
        
        events = dynamic_content.get_upcoming_events(30)  # На 30 дней вперёд
        
        if not events:
            bot.reply_to(message, "📭 Нет запланированных мероприятий\n\nДобавить: `/add_event`", parse_mode="Markdown")
            return
        
        text = "🎉 *МЕРОПРИЯТИЯ:*\n\n"
        for e in events:
            text += f"*#{e['id']}* {e['title']}\n"
            text += f"   📅 {e['date']} в {e['time']}\n"
            text += f"   📝 {e['description']}\n\n"
        
        text += "➖➖➖\n"
        text += "Удалить: `/del_event <id>`"
        
        bot.reply_to(message, text, parse_mode="Markdown")
    
    @bot.message_handler(commands=['del_event'])
    def delete_event_cmd(message: types.Message):
        """Удалить мероприятие"""
        user_id = message.from_user.id
        
        if not is_boss(user_id):
            bot.reply_to(message, "⛔ Только для боссов!")
            return
        
        try:
            event_id = int(message.text.replace('/del_event', '').strip())
            if dynamic_content.deactivate_event(event_id):
                bot.reply_to(message, f"✅ Мероприятие #{event_id} удалено")
                logger.info(f"🗑️ Босс {user_id} удалил мероприятие #{event_id}")
            else:
                bot.reply_to(message, f"❌ Мероприятие #{event_id} не найдено")
        except ValueError:
            bot.reply_to(message, "📝 Формат: `/del_event <id>`", parse_mode="Markdown")
    
    # ==================== СТАТИСТИКА ====================
    
    @bot.message_handler(commands=['content_stats', 'ai_stats'])
    def content_stats_cmd(message: types.Message):
        """Статистика контента и AI памяти"""
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "⛔ Только для админов!")
            return
        
        # Статистика контента
        content_stats = dynamic_content.get_stats()
        
        # Статистика памяти
        memory_stats = user_memory.get_stats()
        
        text = (
            "📊 *СТАТИСТИКА AI SYSTEM v3.0*\n\n"
            "*Динамический контент:*\n"
            f"🎁 Активных акций: {content_stats['active_promotions']}\n"
            f"🎉 Ближайших мероприятий: {content_stats['upcoming_events']}\n"
            f"📢 Объявлений: {content_stats['active_announcements']}\n\n"
            "*Память о гостях:*\n"
            f"👥 Всего профилей: {memory_stats['total_users']}\n"
            f"📝 С именами: {memory_stats['with_names']}\n"
            f"📍 С предпочтениями бара: {memory_stats['with_preferred_bar']}\n"
            f"🥃 С любимыми напитками: {memory_stats['with_favorite_drinks']}\n"
            f"👑 VIP-гостей (10+ визитов): {memory_stats['vip_guests']}\n\n"
            "➖➖➖\n"
            "*Команды:*\n"
            "`/list_promos` - акции\n"
            "`/list_events` - мероприятия\n"
            "`/add_promo` - добавить акцию\n"
            "`/add_event` - добавить мероприятие"
        )
        
        bot.reply_to(message, text, parse_mode="Markdown")
    
    @bot.message_handler(commands=['cleanup_content'])
    def cleanup_content_cmd(message: types.Message):
        """Очистить просроченный контент"""
        user_id = message.from_user.id
        
        if not is_boss(user_id):
            bot.reply_to(message, "⛔ Только для боссов!")
            return
        
        cleaned = dynamic_content.cleanup_expired()
        bot.reply_to(message, f"🧹 Очищено {cleaned} просроченных записей")
    
    # ==================== ОБЪЯВЛЕНИЯ ====================
    
    @bot.message_handler(commands=['announce'])
    def add_announcement_cmd(message: types.Message):
        """Добавить объявление: /announce Текст"""
        user_id = message.from_user.id
        
        if not is_boss(user_id):
            bot.reply_to(message, "⛔ Только для боссов!")
            return
        
        text = message.text.replace('/announce', '').strip()
        
        if not text:
            bot.reply_to(message, "📝 Формат: `/announce Текст объявления`", parse_mode="Markdown")
            return
        
        ann = dynamic_content.add_announcement(text)
        bot.reply_to(message, f"✅ Объявление добавлено (ID: #{ann['id']})")
    
    logger.info("✅ Обработчики управления контентом зарегистрированы")
