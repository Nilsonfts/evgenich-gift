# /ai/knowledge.py
"""
Работа с базой знаний и меню для AI.
"""
# Здесь будет логика поиска и агрегации знаний для AI

from knowledge_base import KNOWLEDGE_BASE_TEXT
from menu_nastoiki import MENU_DATA
from food_menu import FOOD_MENU_DATA

def find_relevant_info(query: str) -> str:
    """
    Находит релевантную информацию в базе знаний и меню по ключевым словам из запроса.
    В будущем — поддержка векторного поиска.
    """
    query_words = {word.lower() for word in query.split()}
    relevant_context = []
    # 1. Поиск в основной базе знаний
    for line in KNOWLEDGE_BASE_TEXT.split('\n'):
        if any(word in line.lower() for word in query_words):
            relevant_context.append(line)
    # 2. Поиск в меню настоек
    for category in MENU_DATA:
        for item in category.get("items", []):
            item_text = f"{category['title']} - {item['name']}: {item.get('narrative_desc', '')}"
            if any(word in item_text.lower() for word in query_words):
                relevant_context.append(item_text)
    # 3. Поиск в меню еды
    for category, items in FOOD_MENU_DATA.items():
        for item in items:
            item_text = f"{category} - {item['name']}: {item.get('narrative_desc', '')}"
            if any(word in item_text.lower() for word in query_words):
                relevant_context.append(item_text)
    if not relevant_context:
        return "Ничего конкретного не нашлось, но я всё равно попробую помочь."
    return "\n".join(relevant_context)
# TODO: добавить функцию vector_search(query) для векторного поиска
