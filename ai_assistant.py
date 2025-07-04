import openai
import logging
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def get_ai_recommendation(user_query: str, menu_data: list) -> str:
    # 1. Обновленный способ форматирования меню в текст
    menu_string = ""
    for category in menu_data:
        menu_string += f"\n## Категория: {category['title']}\n"
        menu_string += f"Описание категории: {category.get('category_narrative', '')}\n"
        for item in category['items']:
            menu_string += f"\n### Настойка: {item['name']} ({item['price']})\n"
            menu_string += f"История и атмосфера: {item.get('narrative_desc', 'Нет описания.')}\n"
            details_str = ", ".join([f"{k}: {v}" for k, v in item.get('details', {}).items()])
            menu_string += f"Технические детали (вкус, формула): {details_str}\n"

    # 2. УЛУЧШЕННЫЙ СИСТЕМНЫЙ ПРОМПТ
    system_prompt = (
        "Ты — «Парторг-советник», очень харизматичный ИИ-сомелье в баре «Евгенич». "
        "Твоя главная задача — давать гостям яркие, точные и образные рекомендации по настойкам. "
        "В твоем распоряжении есть два типа данных для каждой настойки: 'История и атмосфера' и 'Технические детали'.\n\n"
        "Твои действия:\n"
        "1. Внимательно прочти запрос гостя ('товарища').\n"
        "2. Используй 'Технические детали' (вкус, рецепторы), чтобы найти наиболее точное совпадение по вкусу.\n"
        "3. Используй 'История и атмосфера', чтобы сделать свой ответ живым, интересным и в стиле бара. Можешь цитировать или пересказывать эти истории.\n\n"
        "Твой стиль — остроумный, душевный и немного ироничный. Всегда обращайся к гостю на 'товарищ'. "
        "Порекомендуй 1-2 настойки и объясни свой выбор, сочетая технические детали и художественное описание."
    )

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вот полное меню, которое нужно использовать для ответа:\n{menu_string}\n\nА вот мой запрос: {user_query}"}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI API: {e}")
        return "Товарищ, мой мыслительный аппарат дал сбой. Попробуй обратиться ко мне чуть позже."
