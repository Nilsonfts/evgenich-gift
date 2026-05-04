"""
Модуль для чтения конфигурации из админ-панели
Бот читает настройки из web/admin_config/
"""
import json
import os
import logging

# Путь к конфигам админ-панели
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'admin_config')

def load_config(filename, default=None):
    """Загружает конфиг из JSON файла"""
    filepath = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка чтения конфига {filename}: {e}")
    return default or {}

def get_texts():
    """Получить тексты бота"""
    return load_config('texts.json', {
        'greeting_start': 'Привет! 🍷',
        'main_menu': 'Выберите действие:',
        'booking_start': 'Отлично! Давайте забронируем стол.',
        'ask_name': 'Как вас зовут?',
        'ask_phone': 'Укажите ваш телефон:',
        'ask_date': 'На какую дату бронируем?',
        'ask_time': 'На какое время?',
        'ask_guests': 'Сколько будет гостей?',
        'ask_bar': 'Выберите бар:',
        'booking_success': '✅ Бронирование успешно создано!',
        'booking_cancelled': 'Бронирование отменено.',
        'unknown_command': 'Неизвестная команда',
        'no_access': 'У вас нет доступа к этой функции',
        'system_error': 'Произошла ошибка. Попробуйте позже.'
    })

def get_bars():
    """Получить список баров"""
    return load_config('bars.json', [
        {'name': 'СПб, Невский 53', 'code': 'ЕВГ_СПБ_НЕВ', 'emoji': '🍷', 'callback_id': 'bar_nevsky', 'tag': '', 'phone': '', 'menu_url': ''},
        {'name': 'СПб, Рубинштейна 9', 'code': 'ЕВГ_СПБ_РУБ', 'emoji': '💎', 'callback_id': 'bar_rubinstein', 'tag': '', 'phone': '', 'menu_url': ''},
        {'name': 'МСК, Пятницкая 30', 'code': 'ЕВГ_МСК_ПЯТ', 'emoji': '🏛️', 'callback_id': 'bar_pyatnitskaya', 'tag': '', 'phone': '', 'menu_url': ''},
        {'name': 'МСК, Цветной бульвар', 'code': 'ЕВГ_МСК_ЦВЕТ', 'emoji': '🌸', 'callback_id': 'bar_tsvetnoj', 'tag': '', 'phone': '', 'menu_url': ''}
    ])

def get_bar_by_callback(callback_id):
    """Получить бар по callback_id"""
    bars = get_bars()
    for bar in bars:
        if bar.get('callback_id') == callback_id:
            return bar
    return None

def get_ai_settings():
    """Получить настройки AI"""
    return load_config('ai_settings.json', {
        'system_prompt': 'Ты - дружелюбный ассистент бара Евгенич.',
        'tone': 'friendly',
        'bar_info': 'Бар Евгенич - это уютное место в Санкт-Петербурге.',
        'menu_info': 'У нас большой выбор настоек.',
        'rules': 'Бронирование обязательно.',
        'temperature': 0.7,
        'max_tokens': 500,
        'model': 'gpt-3.5-turbo'
    })

def get_staff():
    """Получить список персонала"""
    return load_config('staff.json', {
        'bosses': [],
        'admins': [],
        'smm': []
    })

def get_links():
    """Получить ссылки"""
    return load_config('links.json', {
        'menu_url': 'https://spb.evgenich.bar/menu',
        'booking_url': '',
        'contact_phone': '',
        'whatsapp': '',
        'telegram': '@evgenichbarspb',
        'instagram': '',
        'vk': '',
        'facebook': '',
        'youtube': ''
    })

def is_boss(user_id):
    """Проверка, является ли пользователь боссом"""
    staff = get_staff()
    return any(u['id'] == user_id for u in staff.get('bosses', []))

def is_admin(user_id):
    """Проверка, является ли пользователь админом"""
    staff = get_staff()
    return any(u['id'] == user_id for u in staff.get('admins', []))

def is_smm(user_id):
    """Проверка, является ли пользователь SMM"""
    staff = get_staff()
    return any(u['id'] == user_id for u in staff.get('smm', []))

# Для обратной совместимости - функция проверки доступа
def has_access(user_id, level='admin'):
    """Проверка доступа пользователя
    level: 'boss', 'admin', 'smm'
    """
    if level == 'boss':
        return is_boss(user_id)
    elif level == 'admin':
        return is_boss(user_id) or is_admin(user_id)
    elif level == 'smm':
        return is_boss(user_id) or is_admin(user_id) or is_smm(user_id)
    return False
