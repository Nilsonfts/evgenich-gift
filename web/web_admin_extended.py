# web_admin_extended.py
"""
Расширенная админ-панель с полным функционалом бота
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import json
import datetime
import logging
import os
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты из бота
try:
    import core.database as database
    from core.config import ALL_ADMINS, BOT_TOKEN
    from ai.dynamic_content import DynamicContent
    from modules.staff_manager import StaffManager
    DB_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Ошибка импорта модулей: {e}")
    DB_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем модули
dynamic_content = DynamicContent() if DB_AVAILABLE else None
staff_manager = StaffManager() if DB_AVAILABLE else None

# ==================== ГЛАВНАЯ СТРАНИЦА ====================

@app.route('/')
def dashboard():
    """Главная страница с общей статистикой"""
    try:
        if not DB_AVAILABLE:
            return render_template('dashboard.html', 
                                 error="База данных недоступна",
                                 stats={})
        
        # Получаем статистику
        total_users = len(database.get_all_users())
        active_staff = staff_manager.get_active_staff_count()
        
        # Статистика за последние 24 часа
        yesterday = datetime.datetime.now() - datetime.timedelta(hours=24)
        general_stats = database.get_report_data_for_period(yesterday, datetime.datetime.now())
        
        # Промоакции и события
        promos = dynamic_content.list_active_promotions()
        events = dynamic_content.list_active_events()
        
        stats = {
            'total_users': total_users,
            'active_staff': active_staff,
            'coupons_issued_24h': general_stats[0],
            'coupons_redeemed_24h': general_stats[1],
            'active_promos': len(promos),
            'active_events': len(events)
        }
        
        return render_template('dashboard_extended.html', stats=stats)
    except Exception as e:
        logger.error(f"Ошибка в dashboard: {e}")
        return f"Ошибка: {str(e)}", 500

# ==================== ПРОМОАКЦИИ ====================

@app.route('/promotions')
def promotions():
    """Страница управления промоакциями"""
    if not DB_AVAILABLE:
        return "База данных недоступна", 503
    
    promos = dynamic_content.list_promotions()
    return render_template('promotions.html', promotions=promos)

@app.route('/api/promotions', methods=['GET', 'POST', 'DELETE'])
def api_promotions():
    """API для работы с промоакциями"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'База данных недоступна'}), 503
    
    if request.method == 'GET':
        promos = dynamic_content.list_promotions()
        return jsonify({'success': True, 'promotions': promos})
    
    elif request.method == 'POST':
        data = request.json
        promo_id = dynamic_content.add_promotion(
            title=data['title'],
            description=data['description'],
            bar_id=data.get('bar_id', 'all'),
            start_date=datetime.datetime.fromisoformat(data['start_date']),
            end_date=datetime.datetime.fromisoformat(data['end_date'])
        )
        return jsonify({'success': True, 'promo_id': promo_id})
    
    elif request.method == 'DELETE':
        promo_id = request.json.get('promo_id')
        result = dynamic_content.delete_promotion(promo_id)
        return jsonify({'success': result})

# ==================== СОБЫТИЯ ====================

@app.route('/events')
def events():
    """Страница управления событиями"""
    if not DB_AVAILABLE:
        return "База данных недоступна", 503
    
    events_list = dynamic_content.list_events()
    return render_template('events.html', events=events_list)

@app.route('/api/events', methods=['GET', 'POST', 'DELETE'])
def api_events():
    """API для работы с событиями"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'База данных недоступна'}), 503
    
    if request.method == 'GET':
        events_list = dynamic_content.list_events()
        return jsonify({'success': True, 'events': events_list})
    
    elif request.method == 'POST':
        data = request.json
        event_id = dynamic_content.add_event(
            title=data['title'],
            description=data['description'],
            bar_id=data.get('bar_id', 'all'),
            event_date=datetime.datetime.fromisoformat(data['event_date'])
        )
        return jsonify({'success': True, 'event_id': event_id})
    
    elif request.method == 'DELETE':
        event_id = request.json.get('event_id')
        result = dynamic_content.delete_event(event_id)
        return jsonify({'success': result})

# ==================== РАССЫЛКИ ====================

@app.route('/broadcast')
def broadcast():
    """Страница рассылок"""
    return render_template('broadcast.html')

@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    """API для отправки рассылки"""
    # Здесь будет логика отправки через бота
    data = request.json
    message = data.get('message')
    target = data.get('target', 'all')  # all, active, new
    
    # TODO: Интеграция с ботом для отправки
    return jsonify({
        'success': True, 
        'message': f'Рассылка отправлена для группы: {target}'
    })

# ==================== ПЕРСОНАЛ ====================

@app.route('/staff')
def staff():
    """Страница управления персоналом"""
    if not DB_AVAILABLE:
        return "База данных недоступна", 503
    
    staff_list = database.get_all_staff()
    return render_template('staff_extended.html', staff=staff_list)

@app.route('/api/staff', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_staff():
    """API для работы с персоналом"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'База данных недоступна'}), 503
    
    if request.method == 'GET':
        staff_list = database.get_all_staff()
        return jsonify({'success': True, 'staff': staff_list})
    
    elif request.method == 'POST':
        data = request.json
        # Добавление нового сотрудника
        staff_id = database.add_staff_member(
            full_name=data['full_name'],
            position=data['position'],
            bar_id=data.get('bar_id', 'all')
        )
        return jsonify({'success': True, 'staff_id': staff_id})
    
    elif request.method == 'PUT':
        data = request.json
        # Обновление сотрудника
        result = database.update_staff_member(
            staff_id=data['staff_id'],
            updates=data['updates']
        )
        return jsonify({'success': result})
    
    elif request.method == 'DELETE':
        staff_id = request.json.get('staff_id')
        result = database.deactivate_staff_member(staff_id)
        return jsonify({'success': result})

# ==================== БРОНИРОВАНИЯ ====================

@app.route('/bookings')
def bookings():
    """Страница бронирований"""
    return render_template('bookings.html')

@app.route('/api/bookings')
def api_bookings():
    """API для получения бронирований"""
    # TODO: Получение данных из TinyDB booking_data.json
    try:
        from tinydb import TinyDB
        db = TinyDB('booking_data.json')
        bookings_list = db.all()
        return jsonify({'success': True, 'bookings': bookings_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== НАСТРОЙКИ AI ====================

@app.route('/ai_settings')
def ai_settings():
    """Страница настроек AI"""
    return render_template('ai_settings_extended.html')

@app.route('/api/ai_concepts')
def api_ai_concepts():
    """API для получения концепций AI"""
    # TODO: Загрузка из базы или конфига
    concepts = [
        {'id': 'evgenich', 'name': 'Евгенич (Классический)', 'active': True},
        {'id': 'rvv', 'name': 'РВВ (90-е)', 'active': False},
        {'id': 'nebar', 'name': 'НеБар', 'active': False},
        {'id': 'spletni', 'name': 'Сплетник', 'active': False},
        {'id': 'orbita', 'name': 'Орбита', 'active': False}
    ]
    return jsonify({'success': True, 'concepts': concepts})

# ==================== АНАЛИТИКА ====================

@app.route('/analytics')
def analytics():
    """Расширенная аналитика"""
    return render_template('analytics_extended.html')

@app.route('/api/analytics/users')
def api_analytics_users():
    """Аналитика пользователей"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'База данных недоступна'}), 503
    
    # Статистика по дням за последний месяц
    data = []
    for i in range(30):
        date = datetime.datetime.now() - datetime.timedelta(days=i)
        # TODO: Реальные данные из БД
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'new_users': 5 + (i % 10),
            'active_users': 20 + (i % 15),
            'coupons_issued': 3 + (i % 8),
            'coupons_redeemed': 2 + (i % 6)
        })
    
    data.reverse()
    return jsonify({'success': True, 'data': data})

# ==================== ПОЛЬЗОВАТЕЛИ ====================

@app.route('/users')
def users():
    """Страница списка пользователей"""
    return render_template('users_extended.html')

@app.route('/api/users')
def api_users():
    """API для получения пользователей"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'База данных недоступна'}), 503
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search = request.args.get('search', '')
    
    # Получаем пользователей
    all_users = database.get_all_users()
    
    # Фильтрация по поиску
    if search:
        all_users = [u for u in all_users if 
                    search.lower() in str(u.get('first_name', '')).lower() or
                    search.lower() in str(u.get('username', '')).lower() or
                    search.lower() in str(u.get('phone_number', '')).lower()]
    
    # Пагинация
    start = (page - 1) * per_page
    end = start + per_page
    users_page = all_users[start:end]
    
    return jsonify({
        'success': True,
        'users': users_page,
        'total': len(all_users),
        'page': page,
        'per_page': per_page
    })

# ==================== HEALTH CHECK ====================

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'OK',
        'database': 'connected' if DB_AVAILABLE else 'disconnected',
        'timestamp': datetime.datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🚀 Запуск расширенной админ-панели на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
