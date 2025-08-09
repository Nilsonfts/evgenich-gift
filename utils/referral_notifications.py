#!/usr/bin/env python3
"""
Система автоматических уведомлений о реферальных наградах
"""
import logging
import threading
import time
from datetime import datetime, timedelta
import pytz

import database
from config import BOT_TOKEN
import telebot
from telebot import types

# Создаем бота для уведомлений
notification_bot = None

def init_notification_bot():
    """Инициализирует бота для уведомлений"""
    global notification_bot
    try:
        notification_bot = telebot.TeleBot(BOT_TOKEN)
        logging.info("Бот уведомлений инициализирован")
        return True
    except Exception as e:
        logging.error(f"Ошибка инициализации бота уведомлений: {e}")
        return False

def send_referral_reward_notification(user_id, reward_count, reward_code):
    """
    Отправляет уведомление о готовой награде за рефералов
    """
    try:
        if not notification_bot:
            logging.error("Бот уведомлений не инициализирован")
            return False
        
        # Формируем сообщение о награде
        reward_text = (
            f"🎉 *Ваша награда готова!*\n\n"
            f"За приглашение друзей вы получаете:\n"
            f"🥃 **{reward_count} бесплатную настойку!**\n\n"
            f"📱 Покажите этот код бармену:\n"
            f"`{reward_code}`\n\n"
            f"✨ Спасибо за то, что приводите друзей к нам!"
        )
        
        # Создаем кнопку для бронирования
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("🥃 Получить награду", callback_data="claim_reward"),
            types.InlineKeyboardButton("📍 Забронировать стол", callback_data="start_booking")
        )
        keyboard.row(
            types.InlineKeyboardButton("📖 Посмотреть меню", callback_data="main_menu_choice")
        )
        
        # Отправляем уведомление
        notification_bot.send_message(
            user_id, 
            reward_text, 
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        logging.info(f"Отправлено уведомление о награде пользователю {user_id}: {reward_count} наград")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        return False

def check_and_notify_ready_rewards():
    """
    Проверяет всех пользователей на готовые награды и отправляет уведомления
    """
    try:
        # Получаем всех пользователей с потенциально готовыми наградами
        users_with_referrals = database.get_users_with_pending_rewards()
        
        notifications_sent = 0
        
        for user_id in users_with_referrals:
            try:
                stats = database.get_referral_stats(user_id)
                
                if stats and stats['pending']:
                    # Находим готовые к выдаче награды
                    ready_rewards = []
                    
                    for ref in stats['pending']:
                        if ref['can_claim']:
                            # Проверяем точно, что награда готова
                            eligible, reason = database.check_referral_reward_eligibility(user_id, ref['user_id'])
                            if eligible:
                                ready_rewards.append(ref)
                    
                    if ready_rewards:
                        # Выдаем все готовые награды автоматически
                        total_rewards = 0
                        for ref in ready_rewards:
                            success = database.mark_referral_rewarded(user_id, ref['user_id'])
                            if success:
                                total_rewards += 1
                        
                        if total_rewards > 0:
                            # Генерируем код награды
                            reward_code = f"REF{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            
                            # Отправляем уведомление
                            success = send_referral_reward_notification(user_id, total_rewards, reward_code)
                            
                            if success:
                                notifications_sent += 1
                                
                                # Логируем выдачу награды
                                logging.info(f"Автоматически выдана реферальная награда: пользователь {user_id}, {total_rewards} наград, код {reward_code}")
                
            except Exception as e:
                logging.error(f"Ошибка обработки пользователя {user_id}: {e}")
                continue
        
        if notifications_sent > 0:
            logging.info(f"Отправлено {notifications_sent} уведомлений о реферальных наградах")
        
        return notifications_sent
        
    except Exception as e:
        logging.error(f"Ошибка в проверке готовых наград: {e}")
        return 0

def check_new_referral_completions():
    """
    Проверяет новых рефералов, которые только что получили настойку
    и отправляет уведомления рефереру
    """
    try:
        # Получаем всех рефералов, которые получили настойку в последние 2 часа
        recent_redeemed = database.get_recently_redeemed_referrals(hours=2)
        
        notifications_sent = 0
        
        for referral_info in recent_redeemed:
            try:
                referrer_id = referral_info['referrer_id']
                referral_name = referral_info['first_name'] or referral_info['username'] or f"ID{referral_info['user_id']}"
                
                # Отправляем уведомление рефереру
                notification_text = (
                    f"🎉 *Отличные новости!*\n\n"
                    f"Ваш друг **{referral_name}** получил настойку в баре!\n\n"
                    f"⏰ Через 48 часов вы получите **бесплатную настойку** в качестве награды.\n\n"
                    f"📍 А пока можете забронировать столик и прийти вместе!"
                )
                
                # Кнопки для действий
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(
                    types.InlineKeyboardButton("📍 Забронировать стол", callback_data="start_booking")
                )
                keyboard.row(
                    types.InlineKeyboardButton("🤝 Пригласить еще друзей", callback_data="show_referral_link"),
                    types.InlineKeyboardButton("📖 Меню", callback_data="main_menu_choice")
                )
                
                notification_bot.send_message(
                    referrer_id,
                    notification_text,
                    parse_mode="Markdown", 
                    reply_markup=keyboard
                )
                
                notifications_sent += 1
                logging.info(f"Уведомление о прогрессе реферала отправлено пользователю {referrer_id}")
                
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления о прогрессе реферала: {e}")
                continue
        
        if notifications_sent > 0:
            logging.info(f"Отправлено {notifications_sent} уведомлений о прогрессе рефералов")
            
        return notifications_sent
        
    except Exception as e:
        logging.error(f"Ошибка проверки новых активаций рефералов: {e}")
        return 0

def start_referral_notification_service():
    """
    Запускает службу уведомлений о реферальных наградах
    """
    def notification_loop():
        if not init_notification_bot():
            logging.error("Не удалось запустить службу уведомлений - проблема с инициализацией бота")
            return
        
        logging.info("Запущена служба уведомлений о реферальных наградах")
        
        while True:
            try:
                # Проверяем готовые награды (каждые 30 минут)
                ready_rewards = check_and_notify_ready_rewards()
                
                # Проверяем новые активации рефералов (каждые 30 минут)  
                new_activations = check_new_referral_completions()
                
                # Спим 30 минут
                time.sleep(1800)  # 1800 секунд = 30 минут
                
            except Exception as e:
                logging.error(f"Ошибка в цикле уведомлений: {e}")
                time.sleep(300)  # При ошибке ждем 5 минут
    
    # Запускаем в отдельном потоке
    notification_thread = threading.Thread(target=notification_loop, daemon=True)
    notification_thread.start()
    
    logging.info("Служба реферальных уведомлений запущена в фоновом режиме")

def send_immediate_referral_notification(referrer_id, referral_name):
    """
    Отправляет немедленное уведомление когда реферал получает настойку
    """
    try:
        if not notification_bot:
            if not init_notification_bot():
                return False
        
        notification_text = (
            f"🎉 *Ваш друг получил настойку!*\n\n"
            f"**{referral_name}** активировал свой купон!\n\n"
            f"⏰ Через 48 часов вы получите **бесплатную настойку**\n\n"
            f"📍 Хотите забронировать столик и отпраздновать вместе?"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("📍 Забронировать стол", callback_data="start_booking")
        )
        keyboard.row(
            types.InlineKeyboardButton("🤝 Статистика рефералов", callback_data="show_referral_stats")
        )
        
        notification_bot.send_message(
            referrer_id,
            notification_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        logging.info(f"Немедленное уведомление отправлено рефереру {referrer_id}")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки немедленного уведомления: {e}")
        return False
