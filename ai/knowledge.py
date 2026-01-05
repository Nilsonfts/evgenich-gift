# /ai/knowledge.py
"""
Работа с базой знаний и меню для AI.
Объединяет информацию из разных источников.
"""

from ai.knowledge_base import KNOWLEDGE_BASE_TEXT
from ai.menu_knowledge import (
    NASTOJKI_INFO, KITCHEN_INFO, OTHER_DRINKS, PRICES_INFO,
    get_nastojki_description, get_food_description, 
    search_menu_item, get_menu_summary
)

try:
    from modules.menu_nastoiki import MENU_DATA
    MENU_NASTOIKI_AVAILABLE = True
except ImportError:
    MENU_NASTOIKI_AVAILABLE = False

try:
    from modules.food_menu import FOOD_MENU_DATA
    FOOD_MENU_AVAILABLE = True
except ImportError:
    FOOD_MENU_AVAILABLE = False


def find_relevant_info(query: str) -> str:
    """
    Находит релевантную информацию в базе знаний и меню по ключевым словам из запроса.
    Использует структурированные данные из menu_knowledge.py
    """
    query_lower = query.lower()
    query_words = {word.lower() for word in query.split()}
    relevant_context = []
    
    # 1. Поиск конкретного блюда/напитка
    specific_item = search_menu_item(query)
    if specific_item:
        relevant_context.append(specific_item)
    
    # 2. Определяем категорию запроса
    if any(word in query_lower for word in ['настойк', 'хуба', 'пломбир', 'напиток', 'выпить']):
        relevant_context.append(get_nastojki_description())
        # Детальная инфа о настойках
        if 'хуба' in query_lower:
            relevant_context.append("**Хуба-Буба** — Легендарная! Вкус как жвачка из 90-х. ТОП-1 по популярности! 🥃")
        if 'пломбир' in query_lower or 'фисташк' in query_lower:
            relevant_context.append("**Фисташковый пломбир** — Сливочная настойка с фисташками, как мороженое. ТОП-2! 🥃")
    
    if any(word in query_lower for word in ['еда', 'кухн', 'блюд', 'чебурек', 'пельмен', 'драник']):
        relevant_context.append(get_food_description())
        # Лайфхак про чебуреки
        if 'чебурек' in query_lower:
            relevant_context.append("💡 **Лайфхак:** Заказывай чебурек с сетом настоек — хрустящее тесто смягчает градусы!")
    
    if any(word in query_lower for word in ['меню', 'что есть', 'что заказать']):
        relevant_context.append(get_menu_summary())
    
    if any(word in query_lower for word in ['цен', 'стоим', 'сколько']):
        relevant_context.append(
            f"💰 **Цены:**\n"
            f"Средний чек: {PRICES_INFO['средний_чек']['будни']} в будни, "
            f"{PRICES_INFO['средний_чек']['выходные']} в выходные\n"
            f"Оплата: {', '.join(PRICES_INFO['оплата']['способы'])}"
        )
    
    # 3. Поиск в основной базе знаний
    for line in KNOWLEDGE_BASE_TEXT.split('\n'):
        if any(word in line.lower() for word in query_words):
            relevant_context.append(line)
    
    # 4. LEGACY: Поиск в старых модулях меню (если есть)
    if MENU_NASTOIKI_AVAILABLE:
        for category in MENU_DATA:
            for item in category.get("items", []):
                item_text = f"{category['title']} - {item['name']}: {item.get('narrative_desc', '')}"
                if any(word in item_text.lower() for word in query_words):
                    relevant_context.append(item_text)
    
    if FOOD_MENU_AVAILABLE:
        for category, items in FOOD_MENU_DATA.items():
            for item in items:
                item_text = f"{category} - {item['name']}: {item.get('narrative_desc', '')}"
                if any(word in item_text.lower() for word in query_words):
                    relevant_context.append(item_text)
    
    if not relevant_context:
        return "Ничего конкретного не нашлось, но я всё равно попробую помочь."
    
    # Убираем дубликаты и объединяем
    return "\n".join(dict.fromkeys(relevant_context))


# TODO: добавить функцию vector_search(query) для векторного поиска
