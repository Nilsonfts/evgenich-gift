"""
Тестовая конфигурация для проверки функций
"""

import os

# Устанавливаем минимальные переменные для тестирования
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['CHANNEL_ID'] = '@test_channel'
os.environ['ADMIN_IDS'] = '123,456'
os.environ['HELLO_STICKER_ID'] = 'test_sticker'
os.environ['NASTOYKA_STICKER_ID'] = 'test_sticker'
os.environ['THANK_YOU_STICKER_ID'] = 'test_sticker'
os.environ['REPORT_CHAT_ID'] = '123'

# Тестовые значения
BOT_TOKEN = 'test_token'
CHANNEL_ID = '@test_channel'
ADMIN_IDS = [123, 456]
HELLO_STICKER_ID = 'test_sticker'
NASTOYKA_STICKER_ID = 'test_sticker'
THANK_YOU_STICKER_ID = 'test_sticker'
REPORT_CHAT_ID = 123

# Опциональные
GOOGLE_SHEET_KEY = None
GOOGLE_CREDENTIALS_JSON = None
