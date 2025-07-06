# settings_manager.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

SETTINGS_FILE = Path("bot_settings.json")

# --- Структура настроек по умолчанию ---
DEFAULT_SETTINGS = {
    "promotions": {
        "group_bonus": {
            "is_active": False,
            "min_guests": 4,
            "bonus_text": "графин фирменной хреновухи на стол"
        },
        "happy_hours": {
            "is_active": False,
            "start_time": "16:00",
            "end_time": "19:00",
            "days": [1, 2, 3], # 0=Пн, 1=Вт, 2=Ср, 3=Чт...
            "bonus_text": "Чебурек в подарок к любой настойке"
        },
        "password_of_the_day": {
            "is_active": False,
            "password": "",
            "bonus_text": ""
        }
    }
}

def _load_settings() -> Dict[str, Any]:
    """Загружает настройки из файла или создает новый с дефолтными."""
    if not SETTINGS_FILE.exists():
        logging.info(f"Файл настроек {SETTINGS_FILE} не найден. Создаю новый.")
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_SETTINGS, f, ensure_ascii=False, indent=4)
        return DEFAULT_SETTINGS
    
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Ошибка чтения {SETTINGS_FILE}. Возвращаю дефолтные настройки.")
            return DEFAULT_SETTINGS

def _save_settings(settings: Dict[str, Any]):
    """Сохраняет настройки в файл."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def get_all_settings() -> Dict[str, Any]:
    """Возвращает все текущие настройки."""
    return _load_settings()

def update_setting(path: str, value: Any) -> bool:
    """
    Обновляет настройку по указанному пути.
    Пример: update_setting("promotions.group_bonus.is_active", True)
    """
    try:
        settings = _load_settings()
        keys = path.split('.')
        current_level = settings
        for key in keys[:-1]:
            current_level = current_level[key]
        
        current_level[keys[-1]] = value
        _save_settings(settings)
        logging.info(f"Настройка '{path}' обновлена на значение: {value}")
        return True
    except KeyError:
        logging.error(f"Неверный путь к настройке: {path}")
        return False
    except Exception as e:
        logging.error(f"Не удалось обновить настройку '{path}': {e}")
        return False

def get_setting(path: str) -> Optional[Any]:
    """
    Получает значение настройки по пути.
    Пример: get_setting("promotions.group_bonus.is_active")
    """
    try:
        settings = _load_settings()
        keys = path.split('.')
        value = settings
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        logging.warning(f"Настройка по пути '{path}' не найдена.")
        return None
