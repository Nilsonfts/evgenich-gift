"""
Полная админ-панель бота «Евгенич»
Покрывает ВСЕ функции бота:
  - Дашборд (метрики, графики)
  - Пользователи (поиск, профиль, купоны)
  - Бронирования
  - Рассылки / Broadcast
  - Аналитика / Отчёты
  - Персонал
  - Акции
  - AI-настройки
  - Бары, Тексты, Ссылки

Railway deploy: gunicorn web.app:app --bind 0.0.0.0:$PORT
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash
import json, os, sys, logging, threading, time
from functools import wraps
from datetime import datetime, timedelta
import pytz

# Корень проекта → PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# ── Database (прямое подключение, без core.config) ──
DATABASE_URL = os.getenv('DATABASE_URL', '')
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() in ('true', '1', 'yes')

DB_OK = False
db = None

if USE_POSTGRES and DATABASE_URL:
    try:
        from db.postgres_client import PostgresClient
        _pg = PostgresClient()

        # Обёртка: PostgresClient — экземпляр, а app.py ожидает модуль с функциями
        class _DbBridge:
            """Превращает методы PostgresClient в функции, с безопасным fallback."""
            # Методы, отсутствующие в PostgresClient — возвращаем безопасные дефолты
            _DEFAULTS = {
                'get_recent_activities': lambda *a, **kw: [],
                'get_staff_performance_for_period': lambda *a, **kw: {},
                'get_full_churn_analysis': lambda *a, **kw: None,
                'get_top_referrers_for_month': lambda *a, **kw: [],
                'get_all_staff': lambda *a, **kw: [],
                'update_staff_status': lambda *a, **kw: False,
                'find_user_by_id_or_username': lambda *a, **kw: None,
                'find_user_by_id': lambda uid, **kw: _pg.get_user_by_id(uid),
            }

            def __getattr__(self, name):
                if hasattr(_pg, name):
                    return getattr(_pg, name)
                if name in self._DEFAULTS:
                    return self._DEFAULTS[name]
                # Неизвестный метод → безопасная заглушка
                logging.warning(f"DB method '{name}' not found, returning None")
                return lambda *a, **kw: None

        db = _DbBridge()
        DB_OK = True
        logging.info("✅ Web panel connected to PostgreSQL")
    except Exception as e:
        logging.warning(f"⚠️ PostgreSQL unavailable: {e}")
else:
    logging.warning("⚠️ Database not configured (set DATABASE_URL + USE_POSTGRES=true)")

# ── App ──
app = Flask(__name__, template_folder='templates_full')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'evgenich-secret-2026-full')
app.permanent_session_lifetime = timedelta(hours=12)

ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS_HASH = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'Evgenich83'))

# Config files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE_DIR, 'admin_config')
os.makedirs(CFG, exist_ok=True)

TEXTS_F   = os.path.join(CFG, 'texts.json')
BARS_F    = os.path.join(CFG, 'bars.json')
AI_F      = os.path.join(CFG, 'ai_settings.json')
STAFF_F   = os.path.join(CFG, 'staff.json')
LINKS_F   = os.path.join(CFG, 'links.json')
PROMOS_F  = os.path.join(CFG, 'promotions.json')

MOSCOW_TZ = pytz.timezone('Europe/Moscow')


# ═════════════════════════════════════
#  Helpers
# ═════════════════════════════════════
def _load(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def _save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def login_required(f):
    @wraps(f)
    def inner(*a, **kw):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return inner


def _db_query(func, *args, default=None, **kwargs):
    """Safe DB call wrapper."""
    if not DB_OK:
        return default
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"DB error in {func.__name__}: {e}")
        return default


def _now_msk():
    return datetime.now(MOSCOW_TZ)


def _shift_bounds(dt=None):
    """Возвращает (start, end) текущей смены 12:00–06:00."""
    dt = dt or _now_msk()
    if dt.hour < 6:
        start = (dt - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    else:
        start = dt.replace(hour=12, minute=0, second=0, microsecond=0)
    end = (start + timedelta(hours=18))  # 06:00 следующего дня
    return start, end


# ═════════════════════════════════════
#  Init defaults
# ═════════════════════════════════════
def _init_defaults():
    if not os.path.exists(TEXTS_F):
        _save(TEXTS_F, {
            'greeting_start': 'Привет! 🍷 Добро пожаловать в бар Евгенич!',
            'booking_start': 'Давайте забронируем стол.',
            'ask_name': 'Как вас зовут?',
            'ask_phone': 'Ваш телефон:',
            'ask_date': 'На какую дату бронируем?',
            'ask_time': 'Во сколько?',
            'ask_guests': 'Сколько гостей?',
            'booking_success': '✅ Бронирование создано!',
        })
    if not os.path.exists(BARS_F):
        _save(BARS_F, [
            {'name': 'Невский', 'code': 'ЕВГ_СПБ', 'emoji': '🍷', 'callback_id': 'bar_nevsky'},
            {'name': 'Рубинштейна', 'code': 'ЕВГ_СПБ_РУБ', 'emoji': '💎', 'callback_id': 'bar_rubinstein'},
            {'name': 'Пятницкая МСК', 'code': 'ЕВГ_МСК_ПЯТ', 'emoji': '🏙', 'callback_id': 'bar_pyatnitskaya'},
            {'name': 'Цветной МСК', 'code': 'ЕВГ_МСК_ЦВЕТ', 'emoji': '🌸', 'callback_id': 'bar_tsvetnoj'},
        ])
    if not os.path.exists(AI_F):
        _save(AI_F, {
            'system_prompt': 'Ты — дружелюбный ассистент бара Евгенич.',
            'tone': 'friendly', 'temperature': 0.7,
            'max_tokens': 500, 'model': 'gpt-3.5-turbo',
            'bar_info': '', 'menu_info': '', 'rules': ''
        })
    if not os.path.exists(STAFF_F):
        _save(STAFF_F, {'bosses': [], 'admins': [], 'smm': []})
    if not os.path.exists(LINKS_F):
        _save(LINKS_F, {'menu_url': '', 'phone': '', 'telegram': '', 'instagram': '', 'vk': ''})
    if not os.path.exists(PROMOS_F):
        _save(PROMOS_F, {
            'group_bonus': {'enabled': False, 'min_guests': 6, 'text': 'Графин настойки в подарок!'},
            'happy_hours': {'enabled': False, 'start': '15:00', 'end': '18:00', 'text': 'Скидка 20% на все настойки'},
            'password_of_day': {'enabled': False, 'word': '', 'bonus': 'Шот в подарок'},
        })


_init_defaults()


# ═══════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        if u == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, p):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = u
            return redirect(url_for('dashboard'))
        return render_template('full/login.html', error='Неверный логин или пароль')
    return render_template('full/login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ═══════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════
@app.route('/')
@login_required
def dashboard():
    now = _now_msk()
    shift_start, shift_end = _shift_bounds(now)

    # Total users
    total = _db_query(db.get_broadcast_statistics, default={}) if DB_OK else {}
    total_users = total.get('total', 0) if total else 0
    active_users = total.get('active', 0) if total else 0
    blocked_users = total.get('blocked', 0) if total else 0
    recent_30d = total.get('recent_30d', 0) if total else 0

    # Shift report
    shift_data = _db_query(db.get_report_data_for_period, shift_start, shift_end, default=None)
    issued_today = 0
    redeemed_today = 0
    if shift_data and isinstance(shift_data, tuple) and len(shift_data) >= 2:
        issued_today = shift_data[0] or 0
        redeemed_today = shift_data[1] or 0

    # Staff stats
    staff_stats = _db_query(db.get_staff_performance_for_period, shift_start, shift_end, default={})

    # Recent activities
    recent = _db_query(db.get_recent_activities, limit=15, default=[])

    # Conversion
    conv = round((redeemed_today / issued_today * 100), 1) if issued_today > 0 else 0

    return render_template('full/dashboard.html',
        total_users=total_users, active_users=active_users,
        blocked_users=blocked_users, recent_30d=recent_30d,
        issued_today=issued_today, redeemed_today=redeemed_today,
        conversion=conv, staff_stats=staff_stats or {},
        recent_activities=recent or [],
        shift_start=shift_start.strftime('%H:%M'),
        shift_end=shift_end.strftime('%H:%M'),
        now=now, db_ok=DB_OK, use_postgres=USE_POSTGRES)


# ═══════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════
@app.route('/users')
@login_required
def users_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')

    all_users = _db_query(db.get_all_users, default=[]) or []

    # Filter
    if search:
        q = search.lower()
        all_users = [u for u in all_users if
            (str(u.get('user_id', '')).find(q) >= 0) or
            (u.get('username', '') or '').lower().find(q) >= 0 or
            (u.get('first_name', '') or '').lower().find(q) >= 0]

    if status_filter:
        all_users = [u for u in all_users if u.get('status') == status_filter]

    # Pagination
    per_page = 50
    total_pages = max(1, (len(all_users) + per_page - 1) // per_page)
    page = min(page, total_pages)
    paginated = all_users[(page-1)*per_page : page*per_page]

    # Status counts (из неотфильтрованного списка для корректного подсчёта)
    all_before_filter = _db_query(db.get_all_users, default=[]) or []
    status_counts = {}
    for u in all_before_filter:
        s = u.get('status', 'unknown')
        status_counts[s] = status_counts.get(s, 0) + 1

    return render_template('full/users.html',
        users=paginated, page=page, total_pages=total_pages,
        total_users=len(all_users), search=search,
        status_filter=status_filter, status_counts=status_counts)


@app.route('/users/<int:user_id>')
@login_required
def user_detail(user_id):
    user = _db_query(db.find_user_by_id, user_id, default=None)
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users_list'))

    referral_stats = _db_query(db.get_referral_stats, user_id, default=None)
    return render_template('full/user_detail.html', user=user, referral_stats=referral_stats)


@app.route('/users/<int:user_id>/action', methods=['POST'])
@login_required
def user_action(user_id):
    action = request.form.get('action')
    if action == 'delete':
        _db_query(db.delete_user, user_id)
        flash(f'Пользователь {user_id} удалён', 'success')
        return redirect(url_for('users_list'))
    elif action == 'update_status':
        new_status = request.form.get('status')
        _db_query(db.update_status, user_id, new_status)
        flash(f'Статус обновлён на {new_status}', 'success')
    elif action == 'update_source':
        new_source = request.form.get('source')
        _db_query(db.update_user_source, user_id, new_source)
        flash(f'Источник обновлён', 'success')
    return redirect(url_for('user_detail', user_id=user_id))


# ═══════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════
@app.route('/analytics')
@login_required
def analytics():
    now = _now_msk()

    # Full churn
    churn = _db_query(db.get_full_churn_analysis, default=None)

    # Leaderboard
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    leaders = _db_query(db.get_top_referrers_for_month, 10, default=[])

    # Broadcast stats
    bstats = _db_query(db.get_broadcast_statistics, default={})

    return render_template('full/analytics.html',
        churn=churn, leaders=leaders or [],
        bstats=bstats or {}, now=now)


# ═══════════════════════════════════════════
#  REPORTS (API endpoint for period-based)
# ═══════════════════════════════════════════
@app.route('/api/report', methods=['POST'])
@login_required
def api_report():
    data = request.json or {}
    period = data.get('period', 'shift')
    now = _now_msk()

    if period == 'shift':
        start, end = _shift_bounds(now)
    elif period == '24h':
        start = now - timedelta(hours=24)
        end = now
    elif period == '7d':
        start = now - timedelta(days=7)
        end = now
    elif period == '30d':
        start = now - timedelta(days=30)
        end = now
    else:
        start = now - timedelta(hours=24)
        end = now

    report = _db_query(db.get_report_data_for_period, start, end, default=None)
    staff = _db_query(db.get_staff_performance_for_period, start, end, default={})

    return jsonify({
        'period': period,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'report': report if isinstance(report, dict) else {'issued': report[0] if report else 0, 'redeemed': report[1] if report else 0} if isinstance(report, tuple) else {},
        'staff': staff or {}
    })


# ═══════════════════════════════════════════
#  BROADCAST
# ═══════════════════════════════════════════
@app.route('/broadcast')
@login_required
def broadcast():
    bstats = _db_query(db.get_broadcast_statistics, default={})
    return render_template('full/broadcast.html', stats=bstats or {})


# ═══════════════════════════════════════════
#  STAFF
# ═══════════════════════════════════════════
@app.route('/staff')
@login_required
def staff():
    staff_list = _db_query(db.get_all_staff, False, default=[])
    roles = _load(STAFF_F, {'bosses': [], 'admins': [], 'smm': []})
    return render_template('full/staff.html', staff=staff_list or [], roles=roles)


@app.route('/staff/role', methods=['POST'])
@login_required
def staff_role():
    action = request.form.get('action')  # add / remove
    role = request.form.get('role')      # boss / admin / smm
    uid = request.form.get('user_id', type=int)
    name = request.form.get('name', f'User {uid}')

    roles = _load(STAFF_F, {'bosses': [], 'admins': [], 'smm': []})
    key = 'bosses' if role == 'boss' else ('admins' if role == 'admin' else role)

    if action == 'add':
        if not any(u['id'] == uid for u in roles.get(key, [])):
            roles.setdefault(key, []).append({'id': uid, 'name': name})
    elif action == 'remove':
        roles[key] = [u for u in roles.get(key, []) if u['id'] != uid]

    _save(STAFF_F, roles)
    flash(f'{action.upper()}: {uid} → {role}', 'success')
    return redirect(url_for('staff'))


@app.route('/staff/<int:staff_id>/toggle', methods=['POST'])
@login_required
def staff_toggle(staff_id):
    new_st = request.form.get('status', 'active')
    _db_query(db.update_staff_status, staff_id, new_st)
    flash(f'Статус сотрудника обновлён', 'success')
    return redirect(url_for('staff'))


# ═══════════════════════════════════════════
#  PROMOTIONS
# ═══════════════════════════════════════════
@app.route('/promotions')
@login_required
def promotions():
    data = _load(PROMOS_F, {})
    return render_template('full/promotions.html', promos=data)


@app.route('/promotions/update', methods=['POST'])
@login_required
def promotions_update():
    data = _load(PROMOS_F, {})
    promo = request.form.get('promo')

    if promo == 'group_bonus':
        data['group_bonus'] = {
            'enabled': 'enabled' in request.form,
            'min_guests': int(request.form.get('min_guests', 6)),
            'text': request.form.get('text', ''),
        }
    elif promo == 'happy_hours':
        data['happy_hours'] = {
            'enabled': 'enabled' in request.form,
            'start': request.form.get('start', '15:00'),
            'end': request.form.get('end', '18:00'),
            'text': request.form.get('text', ''),
        }
    elif promo == 'password_of_day':
        data['password_of_day'] = {
            'enabled': 'enabled' in request.form,
            'word': request.form.get('word', ''),
            'bonus': request.form.get('bonus', ''),
        }

    _save(PROMOS_F, data)
    flash('Акция обновлена!', 'success')
    return redirect(url_for('promotions'))


# ═══════════════════════════════════════════
#  AI SETTINGS
# ═══════════════════════════════════════════
@app.route('/ai')
@login_required
def ai_settings():
    data = _load(AI_F, {})
    return render_template('full/ai_settings.html', ai=data)


@app.route('/ai/update', methods=['POST'])
@login_required
def ai_update():
    data = _load(AI_F, {})
    for k in request.form:
        v = request.form[k]
        if k == 'temperature':
            try: v = float(v)
            except: pass
        elif k == 'max_tokens':
            try: v = int(v)
            except: pass
        data[k] = v
    _save(AI_F, data)
    flash('Настройки AI обновлены', 'success')
    return redirect(url_for('ai_settings'))


# ═══════════════════════════════════════════
#  BARS
# ═══════════════════════════════════════════
@app.route('/bars')
@login_required
def bars():
    data = _load(BARS_F, [])
    return render_template('full/bars.html', bars=data)


@app.route('/bars/save', methods=['POST'])
@login_required
def bars_save():
    action = request.form.get('action')
    data = _load(BARS_F, [])

    if action == 'add':
        bar = {
            'name': request.form.get('name'),
            'code': request.form.get('code'),
            'emoji': request.form.get('emoji', '🍷'),
            'callback_id': request.form.get('callback_id'),
            'phone': request.form.get('phone', ''),
            'menu_url': request.form.get('menu_url', ''),
        }
        if not any(b['callback_id'] == bar['callback_id'] for b in data):
            data.append(bar)
            flash(f'Бар «{bar["name"]}» добавлен', 'success')
        else:
            flash('callback_id уже существует', 'error')

    elif action == 'edit':
        cid = request.form.get('callback_id')
        for b in data:
            if b['callback_id'] == cid:
                b['name'] = request.form.get('name')
                b['code'] = request.form.get('code')
                b['emoji'] = request.form.get('emoji')
                b['phone'] = request.form.get('phone', '')
                b['menu_url'] = request.form.get('menu_url', '')
        flash('Бар обновлён', 'success')

    elif action == 'delete':
        cid = request.form.get('callback_id')
        data = [b for b in data if b['callback_id'] != cid]
        flash('Бар удалён', 'success')

    _save(BARS_F, data)
    return redirect(url_for('bars'))


# ═══════════════════════════════════════════
#  TEXTS
# ═══════════════════════════════════════════
@app.route('/texts')
@login_required
def texts():
    data = _load(TEXTS_F, {})
    return render_template('full/texts.html', texts=data)


@app.route('/texts/update', methods=['POST'])
@login_required
def texts_update():
    data = _load(TEXTS_F, {})
    for k in request.form:
        data[k] = request.form[k]
    _save(TEXTS_F, data)
    flash('Тексты сохранены', 'success')
    return redirect(url_for('texts'))


# ═══════════════════════════════════════════
#  LINKS
# ═══════════════════════════════════════════
@app.route('/links')
@login_required
def links():
    data = _load(LINKS_F, {})
    return render_template('full/links.html', links=data)


@app.route('/links/update', methods=['POST'])
@login_required
def links_update():
    data = {}
    # Основные поля
    for k in ['menu_url', 'phone', 'loyalty_url', 'website', 'telegram', 'instagram', 'vk', 'whatsapp']:
        if k in request.form:
            data[k] = request.form[k]
    # Кастомные пары ключ-значение
    keys = request.form.getlist('custom_key[]')
    vals = request.form.getlist('custom_val[]')
    for ck, cv in zip(keys, vals):
        if ck.strip():
            data[ck.strip()] = cv
    _save(LINKS_F, data)
    flash('Ссылки сохранены', 'success')
    return redirect(url_for('links'))


# ═══════════════════════════════════════════
#  API — live stats (AJAX)
# ═══════════════════════════════════════════
@app.route('/api/stats')
@login_required
def api_stats():
    bstats = _db_query(db.get_broadcast_statistics, default={}) or {}
    shift_s, shift_e = _shift_bounds()
    report = _db_query(db.get_report_data_for_period, shift_s, shift_e, default=None)
    issued = 0
    redeemed = 0
    if report and isinstance(report, tuple):
        issued = report[0] or 0
        redeemed = report[1] or 0
    return jsonify({
        'total': bstats.get('total', 0),
        'active': bstats.get('active', 0),
        'blocked': bstats.get('blocked', 0),
        'recent_30d': bstats.get('recent_30d', 0),
        'shift_issued': issued,
        'shift_redeemed': redeemed,
    })


@app.route('/api/users/search')
@login_required
def api_users_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])

    user = _db_query(db.find_user_by_id_or_username, q, default=None)
    if user:
        return jsonify([dict(user) if hasattr(user, 'keys') else {'user_id': q}])
    return jsonify([])


# ═══════════════════════════════════════════
#  LOYALTY — GetMeBack Integration
# ═══════════════════════════════════════════
_GMB_API_KEY = os.getenv('GMB_API_KEY', '')
_GMB_API_URL = os.getenv('GMB_API_URL', 'https://evgenich.getmeback.ru/rest/base/v33/validator/')


def _gmb_call(data: dict):
    """POST к GetMeBack API. Возвращает parsed JSON или None."""
    import requests as req
    if not _GMB_API_KEY:
        return None
    payload = {'api_key': _GMB_API_KEY}
    payload.update(data)
    try:
        r = req.post(_GMB_API_URL, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"GMB API error: {e}")
        return None


def _gmb_parse_client(result):
    """Извлекает данные клиента из ответа GMB."""
    if result is None:
        return None
    if isinstance(result, list):
        return result[0] if result and isinstance(result[0], dict) else None
    if isinstance(result, dict):
        return result
    return None


@app.route('/loyalty')
@login_required
def loyalty():
    return render_template(
        'full/loyalty.html',
        configured=bool(_GMB_API_KEY),
        api_url=_GMB_API_URL
    )


@app.route('/api/loyalty/search')
@login_required
def loyalty_search():
    """Поиск клиента в GMB по телефону / id_client / id_device."""
    if not _GMB_API_KEY:
        return jsonify({'error': 'GMB_API_KEY не настроен'}), 400

    phone = request.args.get('phone', '').strip()
    id_client = request.args.get('id_client', '').strip()
    id_device = request.args.get('id_device', '').strip()

    data = {}
    if phone:
        # Нормализуем телефон
        clean = ''.join(c for c in phone if c.isdigit())
        if len(clean) == 11 and clean.startswith('8'):
            clean = '7' + clean[1:]
        data['phone'] = clean
    elif id_client:
        data['id_client'] = int(id_client)
    elif id_device:
        data['id_device'] = id_device
    else:
        return jsonify({'error': 'Укажите телефон, id_client или id_device'}), 400

    result = _gmb_call(data)
    client = _gmb_parse_client(result)

    if client:
        return jsonify({'client': client})
    return jsonify({'client': None, 'message': 'Клиент не найден'})


@app.route('/api/loyalty/accrue', methods=['POST'])
@login_required
def loyalty_accrue():
    """Начисление бонусов через GMB API."""
    if not _GMB_API_KEY:
        return jsonify({'result': 'error', 'message': 'GMB_API_KEY не настроен'}), 400

    body = request.get_json(force=True)
    id_client = body.get('id_client')
    if not id_client:
        return jsonify({'result': 'error', 'message': 'id_client обязателен'}), 400

    data = {
        'type': 'bonus',
        'id_client': int(id_client),
        'order_price': int(body.get('order_price', 0)),
        'branch_name': body.get('branch_name', 'Евгенич'),
        'manager_name': body.get('manager_name', 'Web Panel'),
        'id_branch': 1,
        'id_manager': 1,
    }
    if body.get('invoice_num'):
        data['invoice_num'] = body['invoice_num']
    if body.get('bonus_value') is not None:
        data['bonus_value'] = int(body['bonus_value'])
    if body.get('paid_bonus'):
        data['paid_bonus'] = int(body['paid_bonus'])

    result = _gmb_call(data)
    if result and isinstance(result, dict):
        return jsonify(result)
    return jsonify({'result': 'error', 'message': 'Пустой ответ от GMB API'})


@app.route('/api/loyalty/gift', methods=['POST'])
@login_required
def loyalty_gift():
    """Выдача подарка через GMB API."""
    if not _GMB_API_KEY:
        return jsonify({'result': 'error', 'message': 'GMB_API_KEY не настроен'}), 400

    body = request.get_json(force=True)
    id_client = body.get('id_client')
    id_gift = body.get('id_gift')
    if not id_client or not id_gift:
        return jsonify({'result': 'error', 'message': 'id_client и id_gift обязательны'}), 400

    result = _gmb_call({
        'type': 'gift',
        'id_client': int(id_client),
        'id_gift': int(id_gift),
        'id_branch': 1,
        'id_manager': 1,
        'branch_name': body.get('branch_name', 'Евгенич'),
        'manager_name': body.get('manager_name', 'Web Panel'),
    })
    if result and isinstance(result, dict):
        return jsonify(result)
    return jsonify({'result': 'error', 'message': 'Пустой ответ от GMB API'})


# ═══════════════════════════════════════════
#  GOOGLE SHEETS → PostgreSQL SYNC
# ═══════════════════════════════════════════
_sync_status = {'running': False, 'progress': '', 'done': False, 'result': None}


def _parse_creds_json(s):
    if not s:
        return None
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s)
    except Exception:
        try:
            return json.loads(" ".join(l.strip() for l in s.splitlines() if l.strip()))
        except Exception:
            return None


def _run_sheets_sync():
    """Фоновая синхронизация Google Sheets → PostgreSQL."""
    global _sync_status
    _sync_status = {'running': True, 'progress': 'Подключение к Google Sheets...', 'done': False, 'result': None}

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_raw = os.getenv('GOOGLE_CREDENTIALS_JSON', '')
        creds_dict = _parse_creds_json(creds_raw)
        if not creds_dict:
            _sync_status.update(running=False, done=True, result={'error': 'GOOGLE_CREDENTIALS_JSON не настроен'})
            return

        sheet_key = os.getenv('GOOGLE_SHEET_KEY', '')
        if not sheet_key:
            _sync_status.update(running=False, done=True, result={'error': 'GOOGLE_SHEET_KEY не настроен'})
            return

        creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_key)

        # Находим лист
        ws = None
        for sheet in spreadsheet.worksheets():
            if 'пользовател' in sheet.title.lower() or 'выгрузка' in sheet.title.lower():
                ws = sheet
                break
        if not ws:
            ws = spreadsheet.sheet1

        _sync_status['progress'] = f'Чтение данных из листа «{ws.title}»...'
        all_rows = ws.get_all_records()
        total = len(all_rows)
        _sync_status['progress'] = f'Найдено {total} строк. Синхронизация с PostgreSQL...'

        if not DB_OK:
            _sync_status.update(running=False, done=True, result={'error': 'БД не подключена'})
            return

        synced = 0
        skipped = 0
        errors = 0

        for i, row in enumerate(all_rows):
            try:
                uid = row.get('user_id') or row.get('Telegram ID') or row.get('ID')
                if not uid:
                    skipped += 1
                    continue
                uid = int(uid)

                # Проверяем, есть ли уже в PostgreSQL
                existing = _db_query(db.get_user_by_id, uid, default=None)
                if existing:
                    skipped += 1
                    continue

                # Добавляем
                username = row.get('username') or row.get('Username') or ''
                first_name = row.get('first_name') or row.get('Имя') or ''
                source = row.get('source') or row.get('Источник') or 'google_sheets_sync'
                status = row.get('status') or row.get('Статус') or 'registered'

                _db_query(db.add_new_user, uid, username, first_name, source)
                if status and status != 'registered':
                    _db_query(db.update_status, uid, status)
                synced += 1

            except Exception as e:
                errors += 1
                logging.error(f"Sync error row {i}: {e}")

            if (i + 1) % 50 == 0:
                _sync_status['progress'] = f'Обработано {i+1}/{total} (добавлено: {synced}, пропущено: {skipped})'

        _sync_status.update(
            running=False, done=True,
            result={'total': total, 'synced': synced, 'skipped': skipped, 'errors': errors}
        )

    except Exception as e:
        logging.error(f"Sheets sync failed: {e}")
        _sync_status.update(running=False, done=True, result={'error': str(e)})


@app.route('/sync')
@login_required
def sync_page():
    return render_template('full/sync.html', status=_sync_status)


@app.route('/sync/start', methods=['POST'])
@login_required
def sync_start():
    if _sync_status.get('running'):
        flash('Синхронизация уже запущена', 'warning')
        return redirect(url_for('sync_page'))
    t = threading.Thread(target=_run_sheets_sync, daemon=True)
    t.start()
    flash('Синхронизация запущена!', 'success')
    return redirect(url_for('sync_page'))


@app.route('/api/sync/status')
@login_required
def sync_status():
    return jsonify(_sync_status)


# ═══════════════════════════════════════════
#  WEB BROADCAST (отправка рассылки через веб)
# ═══════════════════════════════════════════
_broadcast_status = {'running': False, 'progress': '', 'done': False, 'result': None}


def _run_web_broadcast(text, btn_text=None, btn_url=None):
    """Фоновая отправка рассылки через Telegram Bot API."""
    global _broadcast_status
    import requests as req

    bot_token = os.getenv('BOT_TOKEN', '')
    if not bot_token:
        _broadcast_status.update(running=False, done=True, result={'error': 'BOT_TOKEN не настроен'})
        return

    _broadcast_status = {'running': True, 'progress': 'Загрузка списка пользователей...', 'done': False, 'result': None}

    users = _db_query(db.get_all_users_for_broadcast, default=[]) or []
    if not users:
        _broadcast_status.update(running=False, done=True, result={'error': 'Нет пользователей для рассылки'})
        return

    total = len(users)
    sent = 0
    failed = 0
    blocked = 0

    # Inline keyboard
    reply_markup = None
    if btn_text and btn_url:
        reply_markup = json.dumps({
            'inline_keyboard': [[{'text': btn_text, 'url': btn_url}]]
        })

    api_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

    for i, user in enumerate(users):
        uid = user.get('user_id')
        if not uid:
            continue

        payload = {
            'chat_id': uid,
            'text': text,
            'parse_mode': 'HTML',
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup

        try:
            resp = req.post(api_url, json=payload, timeout=10)
            data = resp.json()

            if data.get('ok'):
                sent += 1
            else:
                err_code = data.get('error_code', 0)
                if err_code == 403:
                    blocked += 1
                    _db_query(db.mark_user_blocked, uid)
                elif err_code == 429:
                    retry = data.get('parameters', {}).get('retry_after', 1)
                    time.sleep(retry)
                    resp2 = req.post(api_url, json=payload, timeout=10)
                    if resp2.json().get('ok'):
                        sent += 1
                    else:
                        failed += 1
                else:
                    failed += 1
        except Exception as e:
            failed += 1
            logging.error(f"Broadcast error {uid}: {e}")

        if (i + 1) % 15 == 0:
            pct = round((i + 1) / total * 100, 1)
            _broadcast_status['progress'] = f'{i+1}/{total} ({pct}%) — ✅{sent} ❌{failed} 🚫{blocked}'

        time.sleep(0.05)  # rate limit ~20 msg/sec

    _broadcast_status.update(
        running=False, done=True,
        result={'total': total, 'sent': sent, 'failed': failed, 'blocked': blocked}
    )


@app.route('/broadcast/send', methods=['POST'])
@login_required
def broadcast_send():
    if _broadcast_status.get('running'):
        flash('Рассылка уже идёт, дождитесь завершения', 'warning')
        return redirect(url_for('broadcast'))

    text = request.form.get('text', '').strip()
    if not text:
        flash('Введите текст рассылки', 'error')
        return redirect(url_for('broadcast'))

    btn_text = request.form.get('btn_text', '').strip() or None
    btn_url = request.form.get('btn_url', '').strip() or None

    t = threading.Thread(target=_run_web_broadcast, args=(text, btn_text, btn_url), daemon=True)
    t.start()
    flash('Рассылка запущена! Следите за прогрессом ниже.', 'success')
    return redirect(url_for('broadcast'))


@app.route('/api/broadcast/status')
@login_required
def broadcast_status_api():
    return jsonify(_broadcast_status)


# ═══════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
