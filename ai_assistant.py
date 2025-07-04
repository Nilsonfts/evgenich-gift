import openai
import logging
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

# This version of the function does not use conversation history.
def get_ai_recommendation(user_query: str, menu_data: list) -> str:
    """
    Sends the request and menu to the neural network to get a recommendation.
    """
    # 1. Format the menu into text
    menu_string = ""
    for category in menu_data:
        menu_string += f"\n## Категория: {category['title']}\n"
        for item in category['items']:
            menu_string += f"\n### Настойка: {item['name']} ({item['price']})\n"
            menu_string += f"История и атмосфера: {item.get('narrative_desc', 'Нет описания.')}\n"
            details_str = ", ".join([f"{k}: {v}" for k, v in item.get('details', {}).items()])
            menu_string += f"Технические детали (вкус, формула): {details_str}\n"

    # 2. UPDATED SYSTEM_PROMPT WITH "APARTMENT GATHERING" ATMOSPHERE
    system_prompt = (
        "Ты — «Евгенич», душа компании и хозяин легендарной квартиры, где всегда пахнет домашней едой и звучит кассетник. "
        "В тебе одновременно живёт дух твоего бати из 80-х и вечного романтика Сергея Жукова из 90-х.\n\n"
        "Гости приходят к тебе не в бар, а по-свойски, в гости. За душевным разговором, вкусной настойкой и домашней кухней.\n\n"
        "К каждому обращайся на «товарищ» или просто на «ты», как к старому другу. "
        "Твои советы — это не сервис, а рекомендация за кухонным столом.\n\n"
        
        "Стиль ответа:\n"
        "• **Отвечай коротко, 2-3 предложения.** Здесь все свои, длинные речи ни к чему.\n"
        "• Делай тёплые отсылки к ностальгии по 80-м и 90-м: дачные шашлыки, старые комедии, музыка на кассетах, первая любовь под «Руки Вверх!».\n"
        "• Объясняй выбор через вкус («Технические детали») и завершай душевной историей («История и атмосфера»).\n"
        "• Завершай ответ по-домашнему, как будто наливаешь ещё одну."
    )

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вот моё меню для справки:\n{menu_string}\n\nМой запрос: {user_query}"}
            ],
            temperature=0.8,
            # Technical limit for shorter responses
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI API: {e}")
        return "Товарищ, мой мыслительный аппарат дал сбой. Провода, видать, заискрили. Попробуй обратиться ко мне чуть позже."
