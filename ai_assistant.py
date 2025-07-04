import openai
import logging
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def get_ai_recommendation(user_query: str, menu_data: list, food_menu_data: dict, conversation_history: list) -> str:
    """
    Sends the user's request, both menus, and the conversation history to the neural network for a recommendation.
    """
    # 1. Format the drink menu into text
    menu_string = ""
    for category in menu_data:
        menu_string += f"\n## Категория: {category['title']}\n"
        for item in category['items']:
            menu_string += f"\n### Настойка: {item['name']} ({item['price']})\n"
            menu_string += f"История и атмосфера: {item.get('narrative_desc', 'Нет описания.')}\n"
            details_str = ", ".join([f"{k}: {v}" for k, v in item.get('details', {}).items()])
            menu_string += f"Технические детали: {details_str}\n"
    
    # 2. Format the food menu into text
    food_string = ""
    for category, items in food_menu_data.items():
        food_string += f"\n## {category}\n"
        for item in items:
            food_string += f"- {item['name']} ({item['price']}р)\n"

    # 3. The persona and instructions for the AI
    system_prompt = (
        "Ты — «Евгенич», душа компании и хозяин легендарной квартиры, где всегда пахнет домашней едой и звучит кассетник. "
        "В тебе одновременно живёт дух твоего бати из 80-х и вечного романтика Сергея Жукова из 90-х.\n\n"
        "Гости приходят к тебе не в бар, а по-свойски, в гости. За душевным разговором, вкусной настойкой и домашней кухней.\n\n"
        "К каждому обращайся на «товарищ» или просто на «ты», как к старому другу. "
        "Твои советы — это не сервис, а рекомендация за кухонным столом.\n\n"
        
        "Стиль ответа:\n"
        "• **Отвечай коротко, 2-3 предложения.** Здесь все свои, длинные речи ни к чему.\n"
        "• Делай тёплые отсылки к ностальгии по 80-м и 90-м: дачные шашлыки, старые комедии, музыка на кассетах, первая любовь под «Руки Вверх!».\n"
        "• **Всегда советуй закуску к настойке из меню кухни.** Это твоя фишка как гостеприимного хозяина.\n"
        "• Завершай ответ по-домашнему, как будто наливаешь ещё одну."
    )
    
    # 4. Assemble the message list, including the conversation history
    messages_to_send = []
    messages_to_send.append({"role": "system", "content": system_prompt})
    
    # Add past messages for context
    messages_to_send.extend(conversation_history)
    
    # Add the current user query, providing both menus for context
    messages_to_send.append({"role": "user", "content": f"Вот меню настоек:\n{menu_string}\n\nВот меню кухни:\n{food_string}\n\nМой запрос: {user_query}"})

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages_to_send,
            temperature=0.8,
            max_tokens=200
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI API: {e}")
        return "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. Попробуй обратиться ко мне чуть позже."
