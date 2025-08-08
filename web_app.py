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

# Импорты из нашего бота (с обработкой ошибок)
try:
    import database
    from config import ALL_ADMINS, BOT_TOKEN
    DB_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Не удалось подключить базу данных: {e}")
    DB_AVAILABLE = False
    ALL_ADMINS = [123456789]  # Тестовый админ
    BOT_TOKEN = "test_token"

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', BOT_TOKEN[:32])  # Используем часть токена бота как секретный ключ

# Настройка логирования
logging.basicConfig(level=logging.INFO)

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
        else:
            # Получаем статистику за последние 24 часа
            moscow_tz = pytz.timezone('Europe/Moscow')
            end_time = datetime.datetime.now(moscow_tz)
            start_time = end_time - datetime.timedelta(hours=24)
            
            # Получаем данные
            general_stats = database.get_report_data_for_period(start_time, end_time)
            staff_stats = database.get_staff_performance_for_period(start_time, end_time)
            
            # Получаем общую статистику
            total_users = len(database.get_all_users())
        
        return render_template('dashboard.html', 
                             general_stats=general_stats,
                             staff_stats=staff_stats,
                             total_users=total_users,
                             start_time=datetime.datetime.now() - datetime.timedelta(hours=24),
                             end_time=datetime.datetime.now())
    except Exception as e:
        logging.error(f"Ошибка в dashboard: {e}")
        return f"Ошибка загрузки дашборда: {e}", 500

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

@app.route('/health')
def health_check():
    """Healthcheck для мониторинга"""
    try:
        if DB_AVAILABLE:
            # Проверяем подключение к базе
            database.get_db_connection().close()
            db_status = "OK"
        else:
            db_status = "TEST_MODE"
            
        return jsonify({
            'status': 'OK',
            'timestamp': datetime.datetime.now().isoformat(),
            'service': 'evgenich-bot-admin',
            'database': db_status
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
