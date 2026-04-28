# /ai/proactive_messenger.py
"""
Модуль проактивных сообщений бота в группах
Бот редко, но метко вступает в разговор
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger("evgenich_ai")


class ProactiveMessenger:
    """Управление проактивными сообщениями бота"""
    
    def __init__(self):
        # Шанс ответить на обычное сообщение — ОТКЛЮЧЕНО (были странные "Ну да 😊")
        self.response_chance = 0.0

        # Минимальный интервал между проактивными сообщениями — 3 часа (было 30 мин)
        self.cooldown_minutes = 180

        # Хранилище последних проактивных сообщений по чатам
        self.last_proactive = {}
        
        # Триггерные фразы для реакции
        self.triggers = {
            "photos_videos": {
                "keywords": [
                    "фото", "фотка", "фотки", "снимок", "селфи",
                    "видео", "видос", "ролик", "сторис", "stories",
                    "запись", "записал", "сфоткал",
                ],
                "responses": [
                    "О, классно! 📸 Кидайте больше фоток из бара, интересно посмотреть! 😊",
                    "Ого! Покажите что там у вас творится! 📸",
                    "Хех, видосики из бара всегда топ! 🎥 Делитесь!",
                    "Йоу! 😄 Скидывайте фоточки/видосики - всем интересно!",
                ],
                "chance": 0.10,  # 10% при упоминании фото/видео
            },
            "in_bar": {
                "keywords": [
                    "в баре", "сейчас здесь", "мы тут", "пришли", "на месте",
                    "уже в евгениче", "в евгениче", "сидим", "тусим",
                    "зашли", "пришел", "пришла", "находимся",
                ],
                "responses": [
                    "О! Вы в баре? 😊 Как там атмосфера?",
                    "Круто! 🥃 Как вам там?",
                    "Ого, уже на месте! 🎉 Что заказали?",
                    "Класс! Потом расскажете как было 😊",
                ],
                "chance": 0.07,  # 7% если гости в баре
            },
            "good_vibes": {
                "keywords": [
                    "круто", "класс", "супер", "отлично", "прекрасно",
                    "огонь", "топ", "кайф", "весело", "атмосфера",
                    "понравилось", "классно провели",
                ],
                "responses": [
                    "Рад слышать! 😊",
                    "Вот это кайф! 🎉",
                    "Ага, у нас всегда так! 😄",
                    "Круто что понравилось! 👍",
                ],
                "chance": 0.05,  # 5% на позитив
            },
            "music_karaoke": {
                "keywords": [
                    "караоке", "петь", "спели", "песню", "песни",
                    "музыка", "музон", "трек", "хит", "играет",
                    "танцы", "танцевали", "потанцевать",
                ],
                "responses": [
                    "О, караоке пошло! 🎤 Что пели?",
                    "Танцы-шманцы! 💃🕺",
                    "Музон качает? 🎶",
                    "Караоке у нас всегда зажигает! 🎤",
                ],
                "chance": 0.10,  # 10% при упоминании музыки
            },
            "drinks": {
                "keywords": [
                    "настойка", "настойки", "хуба-буба", "пломбир",
                    "выпили", "пьем", "заказали", "коктейль",
                    "шот", "рюмка", "стопка",
                ],
                "responses": [
                    "Хуба-Буба топ! 🥃",
                    "О, что пробовали?",
                    "Настойки наши - огонь! 🔥",
                    "Вкусно? 😊",
                ],
                "chance": 0.08,  # 8% при упоминании напитков
            },
        }
    
    def should_respond(self, message: str, chat_id: int) -> Optional[str]:
        """
        Определить нужно ли боту проактивно ответить

        Args:
            message: Текст сообщения
            chat_id: ID чата

        Returns:
            None если не нужно отвечать
            str с текстом ответа если нужно
        """

        # Безопасность: пустые / короткие сообщения игнорируем
        if not message or len(message.split()) < 4:
            return None

        # Проверяем cooldown
        if not self._check_cooldown(chat_id):
            return None

        message_lower = message.lower()

        # Проверяем триггеры по приоритету
        for trigger_name, config in self.triggers.items():
            keywords = config["keywords"]
            responses = config["responses"]
            chance = config["chance"]

            # Есть ли ключевые слова?
            if any(keyword in message_lower for keyword in keywords):
                # Бросаем кость
                if random.random() < chance:
                    self._update_cooldown(chat_id)
                    response = random.choice(responses)
                    logger.info(f"🎲 Проактивный ответ в чате {chat_id}: trigger={trigger_name}")
                    return response

        # Случайные generic-реплики ("Ну да", "Хех") удалены — были странными в реальных разговорах
        return None
    
    def _check_cooldown(self, chat_id: int) -> bool:
        """Проверить прошел ли cooldown"""
        if chat_id not in self.last_proactive:
            return True
        
        last_time = self.last_proactive[chat_id]
        elapsed = datetime.now() - last_time
        
        return elapsed > timedelta(minutes=self.cooldown_minutes)
    
    def _update_cooldown(self, chat_id: int):
        """Обновить время последнего проактивного сообщения"""
        self.last_proactive[chat_id] = datetime.now()
    
    def get_stats(self) -> Dict:
        """Получить статистику проактивных сообщений"""
        return {
            "response_chance": self.response_chance,
            "cooldown_minutes": self.cooldown_minutes,
            "active_chats": len(self.last_proactive),
            "triggers": len(self.triggers),
        }


# Глобальный экземпляр
proactive_messenger = ProactiveMessenger()
