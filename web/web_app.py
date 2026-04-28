# web_app.py
"""
Веб-интерфейс для админ-панели бота на Flask
"""

from flask import Flask, render_template, jsonify, request
import json
import datetime
import pytz
import logging
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv

# Загружаем переменные окружения для веб-интерфейса
if os.path.exists('.env.web'):
    # Простая загрузка .env файла
    with open('.env.web', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Исправляем JSON для Google Credentials (убираем лишние кавычки)
if os.getenv('GOOGLE_CREDENTIALS_JSON'):
    credentials = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if credentials.startswith('"') and credentials.endswith('"'):
        os.environ['GOOGLE_CREDENTIALS_JSON'] = credentials[1:-1]

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты из нашего бота (с обработкой ошибок)
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import database
    from core.config import ALL_ADMINS, BOT_TOKEN
    from ai.dynamic_content import DynamicContent
    
    DB_AVAILABLE = True
    dynamic_content = DynamicContent()
    logger.info("✅ Модули базы данных загружены успешно")
except Exception as e:
    logger.warning(f"⚠️ Не удалось подключить базу данных: {e}")
    DB_AVAILABLE = False
    dynamic_content = None
    ALL_ADMINS = [123456789]  # Тестовый админ
    BOT_TOKEN = "test_token"

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', BOT_TOKEN[:32])  # Используем часть токена бота как секретный ключ

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Выводим информацию о статусе подключения
logger.info(f"🌐 Запуск веб-интерфейса...")
logger.info(f"📊 База данных доступна: {DB_AVAILABLE}")
logger.info(f"🔑 Количество админов: {len(ALL_ADMINS)}")
logger.info(f"🐘 PostgreSQL: {os.getenv('USE_POSTGRES', 'false')}")
logger.info(f"📈 Google Sheets: {'Да' if os.getenv('GOOGLE_SHEET_KEY') else 'Нет'}")

# ─────────────────────────────────────────────────────────────
# DEPRECATED LEGACY ENTRYPOINT
# Этот модуль НЕ имеет аутентификации и CSRF-защиты, был оставлен
# для обратной совместимости со старыми Railway-конфигами.
# Используйте web/app.py (web.app:app) — там login + CSRFProtect.
# Чтобы запустить этот модуль, явно установите WEB_APP_LEGACY_ENABLED=1.
# ─────────────────────────────────────────────────────────────
_LEGACY_ENABLED = os.getenv('WEB_APP_LEGACY_ENABLED', '0') == '1'

@app.before_request
def _block_legacy_access():
    """Блокируем все запросы, если legacy-режим явно не включён."""
    if not _LEGACY_ENABLED:
        return (
            "This endpoint has been disabled. "
            "Use the secured admin panel (web.app:app).",
            410,
        )
    return None

def is_admin_authorized(admin_id):
    """Проверяет, является ли пользователь админом"""
    return int(admin_id) in ALL_ADMINS

@app.route('/')
def dashboard():
    """Главная страница дашборда"""
    try:
        if not DB_AVAILABLE:
            # Тестовые данные если база недоступна
            general_stats = (25, 18, 0, {'Прямой заход': 15, 'Персонал': 8, 'Реклама': 2}, 0)
            staff_stats = {
                'Официант': [{'name': 'Иван Петров', 'brought': 12, 'churn': 1, 'position': 'Официант'}],
                'Бармен': [{'name': 'Мария Сидорова', 'brought': 8, 'churn': 0, 'position': 'Бармен'}]
            }
            total_users = 150
            logger.info("📊 Использование тестовых данных для дашборда")
        else:
            try:
                # Получаем статистику за последние 24 часа
                moscow_tz = pytz.timezone('Europe/Moscow')
                end_time = datetime.datetime.now(moscow_tz)
                start_time = end_time - datetime.timedelta(hours=24)
                
                # Получаем данные
                general_stats = database.get_report_data_for_period(start_time, end_time)
                staff_stats = database.get_staff_performance_for_period(start_time, end_time)
                
                # Получаем общую статистику
                total_users = len(database.get_all_users())
                logger.info("📊 Данные загружены из базы данных")
                
            except Exception as db_error:
                logger.error(f"Ошибка работы с базой: {db_error}")
                # Fallback на тестовые данные
                general_stats = (25, 18, 0, {'Прямой заход': 15, 'Персонал': 8, 'Реклама': 2}, 0)
                staff_stats = {
                    'Официант': [{'name': 'Иван Петров', 'brought': 12, 'churn': 1, 'position': 'Официант'}],
                    'Бармен': [{'name': 'Мария Сидорова', 'brought': 8, 'churn': 0, 'position': 'Бармен'}]
                }
                total_users = 150
        
        return render_template('dashboard.html', 
                             general_stats=general_stats,
                             staff_stats=staff_stats,
                             total_users=total_users,
                             start_time=datetime.datetime.now() - datetime.timedelta(hours=24),
                             end_time=datetime.datetime.now(),
                             db_available=DB_AVAILABLE)
    except Exception as e:
        logger.error(f"Критическая ошибка в dashboard: {e}")
        return f"""
        <h1>⚠️ Ошибка загрузки дашборда</h1>
        <p>Детали: {str(e)}</p>
        <p>База данных: {'Подключена' if DB_AVAILABLE else 'Не доступна'}</p>
        <a href='/health'>Проверить статус</a>
        """, 500

@app.route('/api/stats')
def api_stats():
    """API для получения статистики"""
    try:
        days = int(request.args.get('days', 7))
        
        if not DB_AVAILABLE:
            # Тестовые данные
            daily_stats = []
            for i in range(days):
                date = datetime.datetime.now() - datetime.timedelta(days=i)
                issued = max(0, 20 + (i * 2) + (i % 3 * 5))
                redeemed = max(0, int(issued * (0.6 + (i % 4) * 0.1)))
                daily_stats.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'issued': issued,
                    'redeemed': redeemed,
                    'conversion': round((redeemed / issued) * 100, 1) if issued > 0 else 0
                })
            daily_stats.reverse()
        else:
            moscow_tz = pytz.timezone('Europe/Moscow')
            end_time = datetime.datetime.now(moscow_tz)
            start_time = end_time - datetime.timedelta(days=days)
            
            # Получаем данные по дням
            daily_stats = []
            for i in range(days):
                day_end = end_time - datetime.timedelta(days=i)
                day_start = day_end - datetime.timedelta(days=1)
                
                stats = database.get_report_data_for_period(day_start, day_end)
                daily_stats.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'issued': stats[0],
                    'redeemed': stats[1],
                    'conversion': round((stats[1] / stats[0]) * 100, 1) if stats[0] > 0 else 0
                })
            
            daily_stats.reverse()  # От старых к новым
        
        return jsonify({
            'success': True,
            'data': daily_stats
        })
    except Exception as e:
        logging.error(f"Ошибка в api_stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users')
def api_users():
    """API для получения списка пользователей"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        if not DB_AVAILABLE:
            # Тестовые данные пользователей
            test_users = []
            for i in range(100):
                test_users.append({
                    'user_id': 100000 + i,
                    'username': f'user{i}' if i % 3 == 0 else None,
                    'first_name': f'Пользователь {i}',
                    'real_name': f'Иван Иванов {i}' if i % 2 == 0 else None,
                    'phone_number': f'+7999123{i:04d}' if i % 4 == 0 else None,
                    'status': ['registered', 'active', 'redeemed'][i % 3],
                    'source': ['Прямой заход', 'Персонал', 'Реклама'][i % 3],
                    'signup_date': (datetime.datetime.now() - datetime.timedelta(days=i)).isoformat(),
                    'contact_shared_date': (datetime.datetime.now() - datetime.timedelta(days=i-1)).isoformat() if i % 4 == 0 else None,
                    'birth_date': f'1990-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}' if i % 5 == 0 else None,
                    'redeem_date': (datetime.datetime.now() - datetime.timedelta(days=i-2)).isoformat() if i % 3 == 2 else None
                })
            
            # Простая пагинация
            start = (page - 1) * per_page
            end = start + per_page
            users_page = test_users[start:end]
            total = len(test_users)
        else:
            # Получаем всех пользователей (в реальной жизни тут будет пагинация)
            all_users = database.get_all_users()
            
            # Простая пагинация
            start = (page - 1) * per_page
            end = start + per_page
            users_page = all_users[start:end]
            total = len(all_users)
        
        return jsonify({
            'success': True,
            'users': users_page,
            'total': total,
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        logging.error(f"Ошибка в api_users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/users')
def users_page():
    """Страница со списком пользователей"""
    return render_template('users.html')

@app.route('/analytics')
def analytics_page():
    """Страница с детальной аналитикой"""
    return render_template('analytics.html')

@app.route('/debug')
def debug_info():
    """Отладочная страница для диагностики"""
    return f"""
    <h1>🔧 Debug Information</h1>
    <h3>Database Status:</h3>
    <ul>
        <li>DB Available: {DB_AVAILABLE}</li>
        <li>USE_POSTGRES: {os.getenv('USE_POSTGRES')}</li>
        <li>DATABASE_PATH: {os.getenv('DATABASE_PATH')}</li>
        <li>DATABASE_URL set: {'Yes' if os.getenv('DATABASE_URL') else 'No'}</li>
    </ul>
    
    <h3>Environment Variables:</h3>
    <ul>
        <li>BOT_TOKEN set: {'Yes' if os.getenv('BOT_TOKEN') else 'No'}</li>
        <li>GOOGLE_SHEET_KEY set: {'Yes' if os.getenv('GOOGLE_SHEET_KEY') else 'No'}</li>
        <li>PORT: {os.getenv('PORT', '8080')}</li>
        <li>Admins count: {len(ALL_ADMINS)}</li>
    </ul>
    
    <h3>Actions:</h3>
    <ul>
        <li><a href="/">Dashboard</a></li>
        <li><a href="/health">Health Check</a></li>
        <li><a href="/api/stats">API Stats</a></li>
        <li><a href="/users">Users Page</a></li>
    </ul>
    """

@app.route('/health')
def health_check():
    """Healthcheck для мониторинга"""
    try:
        status_info = {
            'status': 'OK',
            'timestamp': datetime.datetime.now().isoformat(),
            'service': 'evgenich-bot-admin',
            'database_available': DB_AVAILABLE,
            'environment': {
                'USE_POSTGRES': os.getenv('USE_POSTGRES'),
                'DATABASE_PATH': os.getenv('DATABASE_PATH'),
                'DATABASE_URL_SET': bool(os.getenv('DATABASE_URL')),
                'GOOGLE_SHEETS_ENABLED': bool(os.getenv('GOOGLE_SHEET_KEY')),
                'BOT_TOKEN_SET': bool(os.getenv('BOT_TOKEN')),
            }
        }
        
        if DB_AVAILABLE:
            try:
                # Проверяем подключение к базе
                database.get_db_connection().close()
                status_info['database_connection'] = "OK"
            except Exception as db_error:
                status_info['database_connection'] = f"ERROR: {str(db_error)}"
                status_info['status'] = 'WARNING'
        else:
            status_info['database_connection'] = "NOT_AVAILABLE"
            
        return jsonify(status_info)
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

# ==================== НОВЫЕ РОУТЫ ====================

@app.route('/promotions')
def promotions():
    """Страница управления промоакциями"""
    return render_template('promotions.html')

@app.route('/api/promotions', methods=['GET', 'POST', 'DELETE'])
def api_promotions():
    """API для работы с промоакциями"""
    if not DB_AVAILABLE or not dynamic_content:
        return jsonify({'success': False, 'error': 'Сервис недоступен'}), 503
    
    try:
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
    except Exception as e:
        logger.error(f"Ошибка в api_promotions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/events')
def events():
    """Страница управления событиями"""
    return render_template('events.html')

@app.route('/api/events', methods=['GET', 'POST', 'DELETE'])
def api_events():
    """API для работы с событиями"""
    if not DB_AVAILABLE or not dynamic_content:
        return jsonify({'success': False, 'error': 'Сервис недоступен'}), 503
    
    try:
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
    except Exception as e:
        logger.error(f"Ошибка в api_events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/broadcast')
def broadcast():
    """Страница рассылок"""
    return render_template('broadcast.html')

@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    """API для отправки рассылки"""
    try:
        data = request.json
        message = data.get('message')
        target = data.get('target', 'all')
        
        # TODO: Интеграция с ботом для реальной отправки
        logger.info(f"Рассылка: target={target}, message_len={len(message)}")
        
        return jsonify({
            'success': True,
            'message': f'Рассылка отправлена для группы: {target}'
        })
    except Exception as e:
        logger.error(f"Ошибка в api_broadcast: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/bookings')
def bookings():
    """Страница бронирований"""
    return render_template('bookings.html')

@app.route('/api/bookings')
def api_bookings():
    """API для получения бронирований"""
    try:
        from tinydb import TinyDB
        db = TinyDB('booking_data.json')
        bookings_list = db.all()
        return jsonify({'success': True, 'bookings': bookings_list})
    except Exception as e:
        logger.error(f"Ошибка в api_bookings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🚀 Запуск веб-сервера на порту {port}")
    logger.info(f"🌐 Railway URL: https://evgenich-gift-production.up.railway.app")
    app.run(host='0.0.0.0', port=port, debug=False)
