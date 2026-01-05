# /texts/user.py
"""
Тексты для пользователей.
Загружаются из админ-панели (web/admin_config/texts.json)
"""
from core.admin_config import get_texts

# Кэшируем тексты
_texts_cache = None

def get_user_texts():
    """Получить все тексты пользователя"""
    global _texts_cache
    if _texts_cache is None:
        _texts_cache = get_texts()
    return _texts_cache

def reload_texts():
    """Перезагрузить тексты из конфига"""
    global _texts_cache
    _texts_cache = None
    return get_user_texts()

# Функции для быстрого доступа к текстам
def greeting_start():
    return get_user_texts().get('greeting_start', 'Привет! 🍷')

def main_menu():
    return get_user_texts().get('main_menu', 'Выберите действие:')

def booking_start():
    return get_user_texts().get('booking_start', 'Отлично! Давайте забронируем стол.')

def ask_name():
    return get_user_texts().get('ask_name', 'Как вас зовут?')

def ask_phone():
    return get_user_texts().get('ask_phone', 'Укажите ваш телефон:')

def ask_date():
    return get_user_texts().get('ask_date', 'На какую дату бронируем?')

def ask_time():
    return get_user_texts().get('ask_time', 'На какое время?')

def ask_guests():
    return get_user_texts().get('ask_guests', 'Сколько будет гостей?')

def ask_bar():
    return get_user_texts().get('ask_bar', 'Выберите бар:')

def booking_success():
    return get_user_texts().get('booking_success', '✅ Бронирование успешно создано!')

def booking_cancelled():
    return get_user_texts().get('booking_cancelled', 'Бронирование отменено.')

def unknown_command():
    return get_user_texts().get('unknown_command', 'Неизвестная команда')

def no_access():
    return get_user_texts().get('no_access', 'У вас нет доступа к этой функции')

def system_error():
    return get_user_texts().get('system_error', 'Произошла ошибка. Попробуйте позже.')
