# /handlers/staff.py
"""
Обработчики управления персоналом.
"""
import core.database as database

def handle_staff_callbacks(bot, keyboards):
    @bot.callback_query_handler(func=lambda call: call.data == 'admin_list_staff' or call.data.startswith('admin_toggle_staff_'))
    def staff_callback(call):
        if call.data == 'admin_list_staff':
            all_staff = database.get_all_staff()
            if not all_staff:
                bot.send_message(call.message.chat.id, "В системе пока нет ни одного сотрудника.")
                return
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "📋 **Список сотрудников:**\n(Нажмите на кнопку под сообщением, чтобы изменить статус)")
            for staff in all_staff:
                status_icon = "✅ Активен" if staff['status'] == 'active' else "❌ Неактивен"
                response = f"{staff['full_name']} ({staff['position']})\nСтатус: {status_icon} | ID: `{staff['telegram_id']}`"
                bot.send_message(call.message.chat.id, response, parse_mode="Markdown", reply_markup=keyboards.get_staff_management_keyboard(staff['staff_id'], staff['status']))
        elif call.data.startswith('admin_toggle_staff_'):
            parts = call.data.split('_')
            staff_id, new_status = int(parts[3]), parts[4]
            if database.update_staff_status(staff_id, new_status):
                all_staff = database.get_all_staff()
                for s in all_staff:
                    if s['staff_id'] == staff_id:
                        status_icon = "✅ Активен" if new_status == 'active' else "❌ Неактивен"
                        new_text = f"{s['full_name']} ({s['position']})\nСтатус: {status_icon} | ID: `{s['telegram_id']}`"
                        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown",
                                              reply_markup=keyboards.get_staff_management_keyboard(s['staff_id'], new_status))
                        break
            else:
                bot.edit_message_text("Не удалось обновить статус.", call.message.chat.id, call.message.message_id, reply_markup=None)
