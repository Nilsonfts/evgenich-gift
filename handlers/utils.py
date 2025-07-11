# /handlers/utils.py
"""
Вспомогательные утилиты для бота.
"""
def shorten_name(full_name: str) -> str:
    """Превращает 'Иван Смирнов' в 'Иван С.'"""
    parts = full_name.split()
    if len(parts) > 1:
        return f"{parts[0]} {parts[1][0]}."
    return full_name
