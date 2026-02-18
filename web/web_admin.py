"""
Админ-панель бота Евгенич
Управление текстами, барами, AI и персоналом
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import json
import os
import sys
from functools import wraps
from datetime import timedelta, datetime

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем database для статистики
try:
    from core import database as db
    DATABASE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ База данных недоступна: {e}")
    DATABASE_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'evgenich-secret-key-2026')
app.permanent_session_lifetime = timedelta(hours=12)

# Конфигурация
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('Evgenich83')

# Файлы конфигурации (используем относительный путь для Railway)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'admin_config')
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR, exist_ok=True)

TEXTS_FILE = os.path.join(CONFIG_DIR, 'texts.json')
BARS_FILE = os.path.join(CONFIG_DIR, 'bars.json')
AI_FILE = os.path.join(CONFIG_DIR, 'ai_settings.json')
STAFF_FILE = os.path.join(CONFIG_DIR, 'staff.json')
LINKS_FILE = os.path.join(CONFIG_DIR, 'links.json')

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Функции для работы с конфигами
def load_config(filename, default=None):
    """Загружает конфиг из JSON файла"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default or {}

def save_config(filename, data):
    """Сохраняет конфиг в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Инициализация дефолтных конфигов
def init_default_configs():
    """Создаёт дефолтные конфиги если их нет"""
    
    # Тексты
    if not os.path.exists(TEXTS_FILE):
        default_texts = {
            'greeting_start': 'Привет! 🍷 Добро пожаловать в бар Евгенич!',
            'main_menu': 'Выберите действие:',
            'booking_start': 'Отлично! Давайте забронируем стол.',
            'ask_name': 'Как вас зовут?',
            'ask_phone': 'Укажите ваш телефон:',
            'ask_date': 'На какую дату бронируем?',
            'ask_time': 'На какое время?',
            'ask_guests': 'Сколько будет гостей?',
            'ask_bar': 'Выберите бар:',
            'booking_success': '✅ Бронирование успешно создано!',
            'booking_cancelled': 'Бронирование отменено.',
            'unknown_command': 'Неизвестная команда',
            'no_access': 'У вас нет доступа к этой функции',
            'system_error': 'Произошла ошибка. Попробуйте позже.'
        }
        save_config(TEXTS_FILE, default_texts)
    
    # Бары
    if not os.path.exists(BARS_FILE):
        default_bars = [
            {'name': 'Невский', 'code': 'ЕВГ_СПБ', 'emoji': '🍷', 'callback_id': 'bar_nevsky'},
            {'name': 'Рубинштейна', 'code': 'ЕВГ_СПБ_РУБ', 'emoji': '💎', 'callback_id': 'bar_rubinstein'},
            {'name': 'Пятницкая МСК', 'code': 'ЕВГ_МСК_ПЯТ', 'emoji': '🏛️', 'callback_id': 'bar_pyatnitskaya'},
            {'name': 'Цветной МСК', 'code': 'ЕВГ_МСК_ЦВЕТ', 'emoji': '🌸', 'callback_id': 'bar_tsvetnoj'}
        ]
        save_config(BARS_FILE, default_bars)
    
    # AI настройки
    if not os.path.exists(AI_FILE):
        default_ai = {
            'system_prompt': 'Ты - дружелюбный ассистент бара Евгенич. Помогаешь гостям с бронированием, отвечаешь на вопросы о меню и настойках.',
            'tone': 'friendly',
            'bar_info': 'Бар Евгенич - это уютное место в Санкт-Петербурге с авторскими настойками.',
            'menu_info': 'У нас большой выбор настоек, коктейлей и закусок.',
            'rules': 'Бронирование обязательно. Мы работаем каждый день.',
            'temperature': 0.7,
            'max_tokens': 500,
            'model': 'gpt-3.5-turbo'
        }
        save_config(AI_FILE, default_ai)
    
    # Персонал
    if not os.path.exists(STAFF_FILE):
        default_staff = {
            'bosses': [{'id': 196614680, 'name': 'Босс 1'}, {'id': 208281210, 'name': 'Босс 2'}],
            'admins': [],
            'smm': [{'id': 1334453330, 'name': 'SMM 1'}, {'id': 208281210, 'name': 'SMM 2'}]
        }
        save_config(STAFF_FILE, default_staff)
    
    # Ссылки
    if not os.path.exists(LINKS_FILE):
        default_links = {
            'menu_url': 'https://spb.evgenich.bar/menu',
            'booking_url': '',
            'contact_phone': '+7 (812) 123-45-67',
            'whatsapp': '',
            'telegram': '@evgenichbarspb',
            'instagram': '',
            'vk': '',
            'facebook': '',
            'youtube': ''
        }
        save_config(LINKS_FILE, default_links)

# Инициализация
init_default_configs()

# ===== РОУТЫ =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница авторизации"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Неверный логин или пароль')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Главная страница"""
    now = datetime.now()
    
    # Заглушки по умолчанию
    stats = {
        'total_users': 0,
        'general_stats': [0, 0, 0],
        'recent_activities': [],
        'top_referrers': [],
        'staff_stats': {},
        'start_time': now - timedelta(hours=24),
        'end_time': now
    }
    
    # Если БД доступна - получаем реальные данные
    if DATABASE_AVAILABLE:
        try:
            # Общее количество пользователей
            stats['total_users'] = db.get_total_users_count()
            
            # Статистика за 24 часа
            stats['general_stats'] = db.get_general_stats_last_24h() or [0, 0, 0]
            
            # Последние активности
            stats['recent_activities'] = db.get_recent_activities(limit=10) or []
            
            # Топ реферралов
            stats['top_referrers'] = db.get_top_referrers_last_24h(limit=10) or []
            
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
    
    return render_template('dashboard.html', **stats)

# ===== УПРАВЛЕНИЕ ТЕКСТАМИ =====

@app.route('/texts')
@login_required
def texts():
    """Страница управления текстами"""
    texts_data = load_config(TEXTS_FILE)
    return render_template('texts.html', texts=texts_data)

@app.route('/texts/update', methods=['POST'])
@login_required
def update_texts():
    """Обновление текстов"""
    texts_data = load_config(TEXTS_FILE)
    section = request.form.get('section')
    
    # Обновляем только поля из формы
    for key in request.form:
        if key != 'section':
            texts_data[key] = request.form[key]
    
    save_config(TEXTS_FILE, texts_data)
    flash(f'Тексты раздела "{section}" успешно обновлены!', 'success')
    return redirect(url_for('texts'))

# ===== УПРАВЛЕНИЕ БАРАМИ =====

@app.route('/bars')
@login_required
def bars():
    """Страница управления барами"""
    bars_data = load_config(BARS_FILE, [])
    return render_template('bars.html', bars=bars_data)

@app.route('/bars/add', methods=['POST'])
@login_required
def add_bar():
    """Добавление нового бара"""
    bars_data = load_config(BARS_FILE, [])
    
    new_bar = {
        'name': request.form.get('name'),
        'code': request.form.get('code'),
        'emoji': request.form.get('emoji', '🍷'),
        'callback_id': request.form.get('callback_id'),
        'tag': request.form.get('tag', ''),
        'phone': request.form.get('phone', ''),
        'menu_url': request.form.get('menu_url', '')
    }
    
    # Проверка на дубликаты
    if any(b['callback_id'] == new_bar['callback_id'] for b in bars_data):
        flash('Бар с таким callback_id уже существует!', 'error')
    else:
        bars_data.append(new_bar)
        save_config(BARS_FILE, bars_data)
        flash(f'Бар "{new_bar["name"]}" успешно добавлен!', 'success')
    
    return redirect(url_for('bars'))

@app.route('/bars/edit', methods=['POST'])
@login_required
def edit_bar():
    """Редактирование бара"""
    bars_data = load_config(BARS_FILE, [])
    callback_id = request.form.get('callback_id')
    
    for bar in bars_data:
        if bar['callback_id'] == callback_id:
            bar['name'] = request.form.get('name')
            bar['code'] = request.form.get('code')
            bar['emoji'] = request.form.get('emoji')
            bar['tag'] = request.form.get('tag', '')
            bar['phone'] = request.form.get('phone', '')
            bar['menu_url'] = request.form.get('menu_url', '')
            break
    
    save_config(BARS_FILE, bars_data)
    flash('Бар успешно обновлён!', 'success')
    return redirect(url_for('bars'))

@app.route('/bars/delete', methods=['POST'])
@login_required
def delete_bar():
    """Удаление бара"""
    bars_data = load_config(BARS_FILE, [])
    callback_id = request.form.get('callback_id')
    
    bars_data = [b for b in bars_data if b['callback_id'] != callback_id]
    save_config(BARS_FILE, bars_data)
    flash('Бар успешно удалён!', 'success')
    return redirect(url_for('bars'))

# ===== НАСТРОЙКИ AI =====

@app.route('/ai')
@login_required
def ai_settings():
    """Страница настроек AI"""
    ai_data = load_config(AI_FILE)
    return render_template('ai_settings.html', ai_settings=ai_data)

@app.route('/ai/update', methods=['POST'])
@login_required
def update_ai():
    """Обновление настроек AI"""
    ai_data = load_config(AI_FILE)
    section = request.form.get('section')
    
    for key in request.form:
        if key != 'section':
            # Преобразуем числовые значения
            value = request.form[key]
            if key in ['temperature', 'max_tokens']:
                try:
                    value = float(value) if key == 'temperature' else int(value)
                except:
                    pass
            ai_data[key] = value
    
    save_config(AI_FILE, ai_data)
    flash(f'Настройки AI успешно обновлены!', 'success')
    return redirect(url_for('ai_settings'))

@app.route('/ai/test', methods=['POST'])
@login_required
def test_ai():
    """Тестирование AI"""
    data = request.json
    query = data.get('query', '')
    
    # Здесь можно добавить реальный вызов AI
    response = f"[Тестовый ответ на: {query}] Это демо-режим. Подключите OpenAI API для реальных ответов."
    
    return jsonify({'response': response})

# ===== УПРАВЛЕНИЕ ПЕРСОНАЛОМ =====

@app.route('/staff')
@login_required
def staff():
    """Страница управления персоналом"""
    staff_data = load_config(STAFF_FILE)
    return render_template('staff.html', staff=staff_data)

@app.route('/staff/add', methods=['POST'])
@login_required
def add_staff():
    """Добавление сотрудника"""
    staff_data = load_config(STAFF_FILE)
    role = request.form.get('role')
    user_id = int(request.form.get('user_id'))
    
    new_user = {'id': user_id, 'name': f'User {user_id}'}
    
    if role == 'boss':
        if not any(u['id'] == user_id for u in staff_data['bosses']):
            staff_data['bosses'].append(new_user)
    elif role == 'admin':
        if not any(u['id'] == user_id for u in staff_data['admins']):
            staff_data['admins'].append(new_user)
    elif role == 'smm':
        if not any(u['id'] == user_id for u in staff_data['smm']):
            staff_data['smm'].append(new_user)
    
    save_config(STAFF_FILE, staff_data)
    flash(f'Пользователь {user_id} добавлен в роль "{role}"!', 'success')
    return redirect(url_for('staff'))

@app.route('/staff/remove', methods=['POST'])
@login_required
def remove_staff():
    """Удаление сотрудника"""
    staff_data = load_config(STAFF_FILE)
    role = request.form.get('role')
    user_id = int(request.form.get('user_id'))
    
    if role == 'boss':
        staff_data['bosses'] = [u for u in staff_data['bosses'] if u['id'] != user_id]
    elif role == 'admin':
        staff_data['admins'] = [u for u in staff_data['admins'] if u['id'] != user_id]
    elif role == 'smm':
        staff_data['smm'] = [u for u in staff_data['smm'] if u['id'] != user_id]
    
    save_config(STAFF_FILE, staff_data)
    flash(f'Пользователь {user_id} удалён из роли "{role}"!', 'success')
    return redirect(url_for('staff'))

@app.route('/links')
@login_required
def links():
    """Управление ссылками"""
    links_data = load_config(LINKS_FILE, {})
    return render_template('links.html', links=links_data)

@app.route('/links/update', methods=['POST'])
@login_required
def update_links():
    """Обновление ссылок"""
    links_data = {
        'menu_url': request.form.get('menu_url', ''),
        'booking_url': request.form.get('booking_url', ''),
        'contact_phone': request.form.get('contact_phone', ''),
        'whatsapp': request.form.get('whatsapp', ''),
        'telegram': request.form.get('telegram', ''),
        'instagram': request.form.get('instagram', ''),
        'vk': request.form.get('vk', ''),
        'facebook': request.form.get('facebook', ''),
        'youtube': request.form.get('youtube', '')
    }
    
    save_config(LINKS_FILE, links_data)
    flash('Ссылки успешно обновлены!', 'success')
    return redirect(url_for('links'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
