# /ai/knowledge.py
"""
Работа с базой знаний для AI.
"""

from ai.knowledge_base import KNOWLEDGE_BASE_TEXT


def find_relevant_info(query: str) -> str:
    """
    Находит релевантную информацию в базе знаний по ключевым словам из запроса.
    """
    query_lower = query.lower()
    query_words = {word.lower() for word in query.split()}
    relevant_context = []
    
    # Поиск в основной базе знаний
    for line in KNOWLEDGE_BASE_TEXT.split('\n'):
        if any(word in line.lower() for word in query_words):
            relevant_context.append(line)
    
    if not relevant_context:
        return "Ничего конкретного не нашлось, но я всё равно попробую помочь."
    
    # Убираем дубликаты и объединяем
    seen = set()
    unique_context = []
    for ctx in relevant_context:
        if ctx not in seen:
            seen.add(ctx)
            unique_context.append(ctx)
    
    return "\n".join(unique_context[:10])
