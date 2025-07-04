import telebot
import os

# Для простоты можно временно вставить токен прямо сюда:
# BOT_TOKEN = "ТВОЙ:ТОКЕН"
# Или, если у тебя настроены переменные окружения на компьютере:
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Не найден токен бота! Укажи его в переменной окружения BOT_TOKEN или впиши прямо в код.")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Отправляет приветствие с инструкцией."""
    bot.send_message(message.chat.id, "Привет! 👋\n\nПросто отправь мне любой стикер, и я пришлю тебе его File ID.")

@bot.message_handler(content_types=['sticker'])
def handle_sticker_id(message):
    """Ловит стикер и отправляет в ответ его ID."""
    sticker_id = message.sticker.file_id
    print(f"Sticker ID: {sticker_id}")
    bot.send_message(message.chat.id, f"ID этого стикера:\n\n`{sticker_id}`", parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'photo', 'audio', 'video', 'document'])
def handle_other_messages(message):
    """Отвечает на любые другие сообщения."""
    bot.reply_to(message, "Это не стикер. Пожалуйста, отправь мне стикер.")


print("Бот для получения ID стикеров запущен...")
print("Отправь боту стикер, чтобы узнать его ID.")
print("Нажми Ctrl + C, чтобы остановить бота.")
bot.infinity_polling()
