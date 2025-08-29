# /handlers/users.py
"""
Обработчики управления пользователями.
"""
import core.database as database

def handle_user_callbacks(bot, admin_states, texts):
    def process_find_user_step(message):
        admin_id = message.from_user.id
        if admin_states.get(admin_id) != 'awaiting_user_identifier':
            return
        identifier = message.text
        user_data = database.find_user_by_id_or_username(identifier)
        if user_data:
            status_map = {
                'registered': 'Зарегистрирован', 'issued': 'Купон выдан',
                'redeemed': 'Купон погашен', 'redeemed_and_left': 'Погасил и отписался'
            }
            status_ru = status_map.get(user_data['status'], user_data['status'])
            staff_name = "Нет"
            if user_data.get('brought_by_staff_id'):
                staff_info = database.find_staff_by_id(user_data['brought_by_staff_id'])
                if staff_info:
                    staff_name = staff_info['short_name']
            response = (f"👤 **Профиль пользователя:**\n\n"
                        f"**ID:** `{user_data['user_id']}`\n"
                        f"**Имя:** {user_data['first_name']}\n"
                        f"**Юзернейм:** @{user_data['username'] or 'Нет'}\n"
                        f"**Статус:** {status_ru}\n"
                        f"**Источник:** {user_data['source'] or 'Неизвестен'}\n"
                        f"**Пригласил:** {user_data['referrer_id'] or 'Никто'}\n"
                        f"**Привел сотрудник:** {staff_name}\n"
                        f"**Дата регистрации:** {user_data['signup_date'] or 'Нет данных'}\n"
                        f"**Дата погашения:** {user_data['redeem_date'] or 'Еще не погашен'}")
            bot.send_message(admin_id, response, parse_mode="Markdown")
        else:
            bot.send_message(admin_id, f"❌ Пользователь с идентификатором '{identifier}' не найден.")
        if admin_id in admin_states:
            del admin_states[admin_id]
    @bot.callback_query_handler(func=lambda call: call.data == 'admin_find_user')
    def find_user_callback(call):
        msg = bot.send_message(call.message.chat.id, "Введите ID или @username пользователя для поиска:")
        admin_states[call.from_user.id] = 'awaiting_user_identifier'
        bot.register_next_step_handler(msg, process_find_user_step)
