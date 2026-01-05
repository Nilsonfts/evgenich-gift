"""
Команды для управления проактивными сообщениями
"""
import logging
from telebot import TeleBot
from ai.proactive_messenger import proactive_messenger
from core.config import ADMIN_IDS

logger = logging.getLogger(__name__)


def register_proactive_commands(bot: TeleBot):
    """Регистрация команд проактивных сообщений"""
    
    @bot.message_handler(commands=['proactive_stats'])
    def proactive_stats_cmd(message):
        """Показать статистику проактивных сообщений"""
        user_id = message.from_user.id
        
        # Проверка прав админа
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ Команда доступна только администраторам")
            return
        
        stats = proactive_messenger.get_stats()
        
        if not stats:
            bot.reply_to(message, "📊 **Статистика проактивных сообщений**\n\n"
                                "Пока нет данных.", parse_mode="Markdown")
            return
        
        # Формируем текст статистики
        text = "📊 **Статистика проактивных сообщений**\n\n"
        
        # Общие данные
        text += f"📈 **Всего отправлено:** {stats['total_sent']}\n"
        text += f"💬 **Активных чатов:** {stats['active_chats']}\n\n"
        
        # Разбивка по типам триггеров
        if stats['by_trigger']:
            text += "🎯 **По типам триггеров:**\n"
            
            trigger_names = {
                'photos_videos': '📸 Фото/видео',
                'in_bar': '🏠 В баре',
                'good_vibes': '✨ Позитив',
                'music_karaoke': '🎤 Музыка/караоке',
                'drinks': '🍹 Напитки',
                'generic': '💭 Общие'
            }
            
            for trigger_type, count in stats['by_trigger'].items():
                name = trigger_names.get(trigger_type, trigger_type)
                percentage = (count / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0
                text += f"  • {name}: {count} ({percentage:.1f}%)\n"
            
            text += "\n"
        
        # Топ активных чатов
        if stats['top_chats']:
            text += "🔝 **Топ-5 активных чатов:**\n"
            for i, (chat_id, count) in enumerate(stats['top_chats'][:5], 1):
                try:
                    chat = bot.get_chat(chat_id)
                    chat_name = chat.title or f"Chat {chat_id}"
                except:
                    chat_name = f"Chat {chat_id}"
                
                text += f"  {i}. {chat_name}: {count} сообщений\n"
        
        bot.reply_to(message, text, parse_mode="Markdown")
        logger.info(f"👤 Админ {user_id} запросил статистику проактивных сообщений")
    
    
    @bot.message_handler(commands=['proactive_reset'])
    def proactive_reset_cmd(message):
        """Сбросить статистику и cooldown'ы"""
        user_id = message.from_user.id
        
        # Проверка прав админа
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ Команда доступна только администраторам")
            return
        
        proactive_messenger.reset_cooldowns()
        bot.reply_to(message, "✅ Статистика и cooldown'ы сброшены")
        logger.info(f"👤 Админ {user_id} сбросил проактивную статистику")


def setup(bot: TeleBot):
    """Setup функция для регистрации"""
    register_proactive_commands(bot)
