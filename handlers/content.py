# /handlers/content.py
"""
Обработчики управления контентом.
"""
def handle_content_callbacks(bot, texts):
    @bot.callback_query_handler(func=lambda call: call.data == 'boss_upload_audio' or call.data == 'boss_set_password')
    def content_callback(call):
        if call.data == 'boss_upload_audio':
            msg = bot.send_message(call.message.chat.id, "Отправь мне аудиофайл...")
            # Здесь должен быть register_next_step_handler для загрузки аудио
        elif call.data == 'boss_set_password':
            msg = bot.send_message(call.message.chat.id, texts.BOSS_ASK_PASSWORD_WORD)
            # Здесь должен быть register_next_step_handler для пароля
