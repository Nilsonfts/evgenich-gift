# /ai/bar_context.py
"""
Контекст бара в реальном времени
"""
import datetime
import logging
import pytz

logger = logging.getLogger("bar_context")

def get_current_bar_context() -> dict:
    """
    Получает текущий контекст бара
    
    Returns:
        dict: Информация о баре сейчас
    """
    tz_moscow = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(tz_moscow)
    hour = now.hour
    day_of_week = now.weekday()  # 0 = Monday, 6 = Sunday
    
    context = {
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%d.%m.%Y"),
        "day_name": _get_day_name(day_of_week),
        "is_open": _is_bar_open(hour, day_of_week),
        "busy_level": _estimate_busy_level(hour, day_of_week),
        "shift_info": _get_shift_info(hour),
        "special_time": _get_special_time_info(hour, day_of_week)
    }
    
    logger.info(f"Контекст бара: {context}")
    return context


def _get_day_name(day_of_week: int) -> str:
    """Возвращает название дня недели"""
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    return days[day_of_week]


def _is_bar_open(hour: int, day_of_week: int) -> bool:
    """Проверяет открыт ли бар"""
    # Бар работает с 12:00 до 06:00 (ночь)
    if hour >= 12 or hour < 6:
        return True
    return False


def _estimate_busy_level(hour: int, day_of_week: int) -> str:
    """
    Оценивает загруженность бара
    
    Returns:
        "empty", "low", "medium", "high", "very_high"
    """
    # Закрыт
    if 6 <= hour < 12:
        return "closed"
    
    # Пятница и суббота
    if day_of_week in [4, 5]:
        if 19 <= hour <= 23 or 0 <= hour < 2:
            return "very_high"
        elif 17 <= hour < 19 or 2 <= hour < 4:
            return "high"
        else:
            return "medium"
    
    # Будние дни
    else:
        if 19 <= hour <= 22:
            return "high"
        elif 17 <= hour < 19 or 22 < hour <= 23:
            return "medium"
        else:
            return "low"


def _get_shift_info(hour: int) -> str:
    """Определяет текущую смену"""
    if 12 <= hour < 18:
        return "дневная смена (12:00-18:00)"
    elif 18 <= hour or hour < 6:
        return "вечерняя смена (18:00-06:00)"
    else:
        return "бар закрыт"


def _get_special_time_info(hour: int, day_of_week: int) -> str:
    """Возвращает информацию об особом времени"""
    # Хэппи хаур (если есть)
    if 16 <= hour < 19 and day_of_week < 5:  # Будни 16-19
        return "🎉 Сейчас Happy Hour!"
    
    # Пиковое время
    if (day_of_week in [4, 5] and 20 <= hour <= 23):
        return "🔥 Пиковое время - много гостей!"
    
    # Спокойное время
    if 12 <= hour < 16:
        return "☕ Спокойное дневное время - идеально для тихого общения"
    
    # Поздняя ночь
    if 2 <= hour < 6:
        return "🌙 Поздняя ночь - уютная атмосфера для задушевных бесед"
    
    return ""


def get_bar_info_text(context: dict) -> str:
    """
    Формирует текстовое описание контекста бара для AI
    """
    parts = []
    
    # Время и открытость
    if context["is_open"]:
        parts.append(f"Сейчас {context['time']}, {context['day_name']}, бар открыт.")
    else:
        parts.append(f"Сейчас {context['time']}, {context['day_name']}, бар закрыт (работаем с 12:00 до 06:00).")
    
    # Загруженность
    busy_texts = {
        "closed": "Бар закрыт.",
        "empty": "В баре пусто, самое время для спокойной беседы.",
        "low": "В баре немного гостей, спокойная атмосфера.",
        "medium": "В баре средняя загруженность, комфортная обстановка.",
        "high": "В баре довольно много гостей, живая атмосфера!",
        "very_high": "В баре аншлаг! Все столики заняты, очень оживленно."
    }
    parts.append(busy_texts.get(context["busy_level"], ""))
    
    # Особая информация
    if context["special_time"]:
        parts.append(context["special_time"])
    
    return " ".join(parts)


def get_location_info() -> dict:
    """Возвращает информацию о локациях баров"""
    return {
        "evgenich_spb": {
            "name": "Евгенич на Невском",
            "address": "Невский проспект, 90-92, Санкт-Петербург",
            "metro": "Маяковская, Площадь Восстания",
            "phone": "+7 (812) 123-45-67",
            "coords": "59.931456, 30.359678"
        },
        "evgenich_msk": {
            "name": "Евгенич в Москве",
            "address": "ул. Большая Дмитровка, 32, Москва",
            "metro": "Чеховская, Пушкинская",
            "phone": "+7 (495) 123-45-67",
            "coords": "55.764089, 37.608542"
        }
    }


def get_working_hours() -> str:
    """Возвращает часы работы"""
    return "Ежедневно с 12:00 до 06:00 (ночь)"
