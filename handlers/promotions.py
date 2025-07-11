# /handlers/promotions.py
"""
Обработчики управления акциями.
"""
def handle_promotions_callbacks(bot, settings_manager, keyboards):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('boss_toggle_'))
    def promotions_callback(call):
        feature_path = call.data.replace('boss_toggle_', '')
        current_value = settings_manager.get_setting(feature_path)
        settings_manager.update_setting(feature_path, not current_value)
        new_settings = settings_manager.get_all_settings()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboards.get_admin_promotions_menu(new_settings))
