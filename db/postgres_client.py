"""
Модуль для работы с базой данных PostgreSQL.
"""
import logging
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.sql import select, insert, update, delete
from sqlalchemy.exc import SQLAlchemyError
import datetime
import pytz

from config import DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

class PostgresClient:
    def __init__(self, db_url=None):
        """
        Инициализирует подключение к PostgreSQL.
        
        Args:
            db_url (str, optional): URL для подключения к PostgreSQL.
        """
        self.db_url = db_url or DATABASE_URL
        self.engine = None
        self.metadata = MetaData()
        
        # Определяем таблицы
        self.users_table = None
        self.staff_table = None
        self.bookings_table = None
        self.events_table = None
        self.settings_table = None
        self.game_results_table = None
        
        self._init_engine()
        self._define_tables()
    
    def _init_engine(self):
        """Инициализирует SQLAlchemy engine."""
        try:
            self.engine = create_engine(self.db_url)
            logging.info(f"PostgreSQL engine initialized with URL: {self.db_url}")
        except Exception as e:
            logging.error(f"Failed to initialize PostgreSQL engine: {e}")
            raise
    
    def _define_tables(self):
        """Определяет структуру таблиц."""
        # Таблица пользователей
        self.users_table = Table(
            'users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, nullable=False, unique=True),
            Column('username', String(100)),
            Column('first_name', String(100)),
            Column('status', String(20), default='new'),
            Column('register_date', DateTime, default=datetime.datetime.now),
            Column('last_activity', DateTime, default=datetime.datetime.now),
            Column('source', String(50)),
            Column('referrer_id', Integer),
            Column('brought_by_staff_id', Integer),
            Column('redeem_date', DateTime),
            Column('referrer_rewarded', Boolean, default=False),
            Column('referrer_rewarded_date', DateTime),
        )
        
        # Таблица сотрудников
        self.staff_table = Table(
            'staff', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('telegram_id', Integer, nullable=False, unique=True),
            Column('full_name', String(100)),
            Column('position', String(50)),
            Column('status', String(20), default='active'),
        )
        
        # Таблица бронирований
        self.bookings_table = Table(
            'bookings', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('date', DateTime, nullable=False),
            Column('time', String(10), nullable=False),
            Column('guests', Integer),
            Column('name', String(100)),
            Column('phone', String(20)),
            Column('comment', Text),
            Column('status', String(20), default='new'),
            Column('created', DateTime, default=datetime.datetime.now),
            Column('source', String(50)),
            Column('source_detail', String(100)),
        )
        
        # Таблица событий
        self.events_table = Table(
            'events', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer),
            Column('event_type', String(50), nullable=False),
            Column('event_data', Text),
            Column('timestamp', DateTime, default=datetime.datetime.now),
        )
        
        # Таблица настроек
        self.settings_table = Table(
            'settings', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('key', String(100), unique=True, nullable=False),
            Column('value', Text),
            Column('updated', DateTime, default=datetime.datetime.now),
        )
        
        # Таблица результатов игр
        self.game_results_table = Table(
            'game_results', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('game_type', String(50), nullable=False),
            Column('result', String(50)),
            Column('points', Integer, default=0),
            Column('timestamp', DateTime, default=datetime.datetime.now),
        )
    
    def create_tables(self):
        """Создает таблицы в базе данных."""
        try:
            self.metadata.create_all(self.engine)
            logging.info("PostgreSQL tables created successfully")
            return True
        except SQLAlchemyError as e:
            logging.error(f"Failed to create PostgreSQL tables: {e}")
            return False
    
    def add_new_user(self, user_id, username, first_name, source, referrer_id=None, brought_by_staff_id=None):
        """
        Добавляет нового пользователя в базу данных.
        
        Args:
            user_id (int): ID пользователя Telegram
            username (str): Имя пользователя
            first_name (str): Имя пользователя
            source (str): Источник регистрации
            referrer_id (int, optional): ID пользователя, пригласившего этого пользователя
            brought_by_staff_id (int, optional): ID сотрудника, приведшего клиента
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                query = select(self.users_table).where(self.users_table.c.user_id == user_id)
                result = connection.execute(query).fetchone()
                
                if result:
                    logging.info(f"PostgreSQL | Пользователь {user_id} уже существует")
                    return False
                
                stmt = insert(self.users_table).values(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    source=source,
                    referrer_id=referrer_id,
                    brought_by_staff_id=brought_by_staff_id,
                    register_date=datetime.datetime.now(pytz.timezone('Europe/Moscow')),
                    last_activity=datetime.datetime.now(pytz.timezone('Europe/Moscow'))
                )
                connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | Пользователь {user_id} добавлен. Источник: {source}, Сотрудник: {brought_by_staff_id}")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка добавления пользователя {user_id}: {e}")
            return False

    def update_status(self, user_id, new_status):
        """
        Обновляет статус пользователя.
        
        Args:
            user_id (int): ID пользователя
            new_status (str): Новый статус
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                stmt = update(self.users_table).where(
                    self.users_table.c.user_id == user_id
                ).values(
                    status=new_status,
                    last_activity=datetime.datetime.now(pytz.timezone('Europe/Moscow'))
                )
                connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | Статус пользователя {user_id} обновлен на {new_status}.")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка обновления статуса для {user_id}: {e}")
            return False

    def add_booking(self, user_id, date, time, guests, name, phone, comment, source="bot", source_detail=None):
        """
        Добавляет новое бронирование в базу данных.
        
        Args:
            user_id (int): ID пользователя
            date (datetime.date): Дата бронирования
            time (str): Время бронирования
            guests (int): Количество гостей
            name (str): Имя бронирующего
            phone (str): Телефон
            comment (str): Комментарий
            source (str): Источник бронирования
            source_detail (str, optional): Дополнительная информация об источнике
        
        Returns:
            int: ID бронирования или None в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                stmt = insert(self.bookings_table).values(
                    user_id=user_id,
                    date=date,
                    time=time,
                    guests=guests,
                    name=name,
                    phone=phone,
                    comment=comment,
                    source=source,
                    source_detail=source_detail,
                    created=datetime.datetime.now(pytz.timezone('Europe/Moscow')),
                    status='new'
                )
                result = connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | Бронирование добавлено для пользователя {user_id}")
                return result.inserted_primary_key[0]
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка добавления бронирования для {user_id}: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """
        Получает информацию о пользователе по его ID.
        
        Args:
            user_id (int): ID пользователя
        
        Returns:
            dict: Данные пользователя или None если не найден
        """
        try:
            with self.engine.connect() as connection:
                query = select(self.users_table).where(self.users_table.c.user_id == user_id)
                result = connection.execute(query).fetchone()
                
                if result:
                    return dict(result)
                return None
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка получения пользователя {user_id}: {e}")
            return None

    def get_all_users(self):
        """
        Получает список всех пользователей.
        
        Returns:
            list: Список словарей с данными пользователей
        """
        try:
            with self.engine.connect() as connection:
                query = select(self.users_table)
                result = connection.execute(query).fetchall()
                
                return [dict(row) for row in result]
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка получения списка пользователей: {e}")
            return []
    
    def add_event(self, user_id, event_type, event_data=None):
        """
        Добавляет новое событие в базу данных.
        
        Args:
            user_id (int): ID пользователя
            event_type (str): Тип события
            event_data (str, optional): Дополнительные данные события
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                stmt = insert(self.events_table).values(
                    user_id=user_id,
                    event_type=event_type,
                    event_data=event_data,
                    timestamp=datetime.datetime.now(pytz.timezone('Europe/Moscow'))
                )
                connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | Событие {event_type} добавлено для пользователя {user_id}")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка добавления события для {user_id}: {e}")
            return False

    def get_setting(self, key, default=None):
        """
        Получает значение настройки по ключу.
        
        Args:
            key (str): Ключ настройки
            default (any, optional): Значение по умолчанию
        
        Returns:
            str: Значение настройки или default, если настройка не найдена
        """
        try:
            with self.engine.connect() as connection:
                query = select(self.settings_table.c.value).where(self.settings_table.c.key == key)
                result = connection.execute(query).fetchone()
                
                if result:
                    return result[0]
                return default
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка получения настройки {key}: {e}")
            return default

    def set_setting(self, key, value):
        """
        Устанавливает значение настройки.
        
        Args:
            key (str): Ключ настройки
            value (str): Значение настройки
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                # Проверяем, существует ли уже такая настройка
                query = select(self.settings_table).where(self.settings_table.c.key == key)
                result = connection.execute(query).fetchone()
                
                if result:
                    # Обновляем существующую настройку
                    stmt = update(self.settings_table).where(
                        self.settings_table.c.key == key
                    ).values(
                        value=value,
                        updated=datetime.datetime.now(pytz.timezone('Europe/Moscow'))
                    )
                else:
                    # Создаем новую настройку
                    stmt = insert(self.settings_table).values(
                        key=key,
                        value=value,
                        updated=datetime.datetime.now(pytz.timezone('Europe/Moscow'))
                    )
                
                connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | Настройка {key} установлена")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка установки настройки {key}: {e}")
            return False
    
    def add_game_result(self, user_id, game_type, result, points=0):
        """
        Добавляет результат игры.
        
        Args:
            user_id (int): ID пользователя
            game_type (str): Тип игры
            result (str): Результат игры
            points (int, optional): Очки
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                stmt = insert(self.game_results_table).values(
                    user_id=user_id,
                    game_type=game_type,
                    result=result,
                    points=points,
                    timestamp=datetime.datetime.now(pytz.timezone('Europe/Moscow'))
                )
                connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | Результат игры {game_type} добавлен для пользователя {user_id}")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка добавления результата игры для {user_id}: {e}")
            return False

    def get_user_game_stats(self, user_id, game_type=None):
        """
        Получает статистику игр пользователя.
        
        Args:
            user_id (int): ID пользователя
            game_type (str, optional): Тип игры для фильтрации
        
        Returns:
            list: Список результатов игр
        """
        try:
            with self.engine.connect() as connection:
                if game_type:
                    query = select(self.game_results_table).where(
                        (self.game_results_table.c.user_id == user_id) & 
                        (self.game_results_table.c.game_type == game_type)
                    )
                else:
                    query = select(self.game_results_table).where(
                        self.game_results_table.c.user_id == user_id
                    )
                
                result = connection.execute(query).fetchall()
                
                return [dict(row) for row in result]
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка получения статистики игр для {user_id}: {e}")
            return []

    def update_user_concept(self, user_id, concept):
        """
        Обновляет AI концепцию пользователя.
        
        Args:
            user_id (int): ID пользователя
            concept (str): Новая концепция AI ассистента
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            with self.engine.connect() as connection:
                stmt = update(self.users_table).where(
                    self.users_table.c.user_id == user_id
                ).values(ai_concept=concept)
                
                connection.execute(stmt)
                connection.commit()
                
                logging.info(f"PostgreSQL | AI концепция пользователя {user_id} обновлена на {concept}")
                return True
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка обновления концепции пользователя {user_id}: {e}")
            return False

    def get_report_data_for_period(self, start_time: datetime.datetime, end_time: datetime.datetime) -> tuple:
        """Получает данные для отчета за период из PostgreSQL."""
        try:
            with self.engine.connect() as connection:
                # Количество выданных подарков (issued)
                # В PostgreSQL используется register_date вместо signup_date
                issued_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.register_date >= start_time,
                        self.users_table.c.register_date <= end_time,
                        self.users_table.c.status.in_(['issued', 'redeemed', 'redeemed_and_left'])
                    )
                )
                issued_count = connection.execute(issued_stmt).scalar() or 0
                
                # Количество активированных подарков (redeemed)
                # Пока используем register_date, так как redeem_date может отсутствовать
                redeemed_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.register_date >= start_time,
                        self.users_table.c.register_date <= end_time,
                        self.users_table.c.status.in_(['redeemed', 'redeemed_and_left'])
                    )
                )
                redeemed_count = connection.execute(redeemed_stmt).scalar() or 0
                
                # Источники трафика
                sources_stmt = select(
                    self.users_table.c.source,
                    sa.func.count().label('count')
                ).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.register_date >= start_time,
                        self.users_table.c.register_date <= end_time
                    )
                ).group_by(self.users_table.c.source)
                
                sources_result = connection.execute(sources_stmt).fetchall()
                all_sources = {(row.source or 'direct'): row.count for row in sources_result}
                
                # Фильтруем источники
                sources = {k: v for k, v in all_sources.items() if k != "staff"}
                staff_count = all_sources.get("staff", 0)
                if staff_count > 0:
                    sources["staff"] = staff_count
                
                # Общее время до активации (пока 0, так как нет redeem_date)
                total_redeem_time_seconds = 0
                
                logging.info(f"PostgreSQL | Отчет за период: выдано {issued_count}, активировано {redeemed_count}")
                return issued_count, redeemed_count, [], sources, total_redeem_time_seconds
                
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка получения данных отчета: {e}")
            return 0, 0, [], {}, 0

    def get_daily_churn_data(self, start_time: datetime.datetime, end_time: datetime.datetime) -> tuple:
        """Получает данные об оттоке за период из PostgreSQL."""
        try:
            with self.engine.connect() as connection:
                # Всего активировано (используем register_date)
                redeemed_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.register_date >= start_time,
                        self.users_table.c.register_date <= end_time,
                        self.users_table.c.status.in_(['redeemed', 'redeemed_and_left'])
                    )
                )
                redeemed_total = connection.execute(redeemed_stmt).scalar() or 0
                
                # Покинуло заведение (используем register_date)
                left_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.register_date >= start_time,
                        self.users_table.c.register_date <= end_time,
                        self.users_table.c.status == 'redeemed_and_left'
                    )
                )
                left_count = connection.execute(left_stmt).scalar() or 0
                
                logging.info(f"PostgreSQL | Отток за период: активировано {redeemed_total}, ушло {left_count}")
                return redeemed_total, left_count
                
        except SQLAlchemyError as e:
            logging.error(f"PostgreSQL | Ошибка получения данных об оттоке: {e}")
            return 0, 0

    # --- Методы для реферальной системы наград ---

    def check_referral_reward_eligibility(self, referrer_id, referred_id):
        """
        Проверяет, можно ли выдать награду за реферала
        """
        try:
            with self.engine.connect() as connection:
                # Находим реферала
                stmt = select(
                    self.users_table.c.register_date,
                    self.users_table.c.redeem_date,
                    self.users_table.c.referrer_rewarded
                ).where(
                    sa.and_(
                        self.users_table.c.user_id == referred_id,
                        self.users_table.c.referrer_id == referrer_id
                    )
                )
                result = connection.execute(stmt).fetchone()
                
                if not result:
                    return False, "Реферал не найден"
                
                register_date, redeem_date, referrer_rewarded = result
                
                # Проверяем, была ли уже выдана награда
                if referrer_rewarded:
                    return False, "Награда уже была выдана"
                
                # Проверяем, получил ли реферал настойку
                if not redeem_date:
                    return False, "Реферал еще не получил настойку"
                
                # Проверяем, прошло ли 48 часов
                current_time = datetime.datetime.now(pytz.utc)
                hours_passed = (current_time - register_date).total_seconds() / 3600
                
                if hours_passed < 48:
                    hours_left = 48 - hours_passed
                    return False, f"До получения награды осталось {int(hours_left)} часов"
                
                return True, "Можно выдать награду"
                
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка проверки права на награду: {e}")
            return False, "Ошибка проверки"

    def mark_referral_rewarded(self, referrer_id, referred_id):
        """
        Отмечает, что награда за реферала была выдана
        """
        try:
            with self.engine.connect() as connection:
                stmt = update(self.users_table).where(
                    sa.and_(
                        self.users_table.c.user_id == referred_id,
                        self.users_table.c.referrer_id == referrer_id
                    )
                ).values(
                    referrer_rewarded=True,
                    referrer_rewarded_date=datetime.datetime.now(pytz.utc)
                )
                
                result = connection.execute(stmt)
                connection.commit()
                return result.rowcount > 0
                
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка отметки награды: {e}")
            return False

    def get_referral_stats(self, user_id):
        """
        Получает статистику по рефералам пользователя
        """
        try:
            with self.engine.connect() as connection:
                # Общее количество рефералов
                total_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    self.users_table.c.referrer_id == user_id
                )
                total_referrals = connection.execute(total_stmt).scalar() or 0
                
                # Количество рефералов, получивших настойку
                redeemed_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.referrer_id == user_id,
                        self.users_table.c.redeem_date.isnot(None)
                    )
                )
                redeemed_referrals = connection.execute(redeemed_stmt).scalar() or 0
                
                # Количество полученных наград
                rewards_stmt = select(sa.func.count()).select_from(self.users_table).where(
                    sa.and_(
                        self.users_table.c.referrer_id == user_id,
                        self.users_table.c.referrer_rewarded == True
                    )
                )
                rewards_received = connection.execute(rewards_stmt).scalar() or 0
                
                # Рефералы, ожидающие 48 часов
                pending_stmt = select(
                    self.users_table.c.user_id,
                    self.users_table.c.username,
                    self.users_table.c.first_name,
                    self.users_table.c.register_date,
                    self.users_table.c.redeem_date
                ).where(
                    sa.and_(
                        self.users_table.c.referrer_id == user_id,
                        self.users_table.c.redeem_date.isnot(None),
                        self.users_table.c.referrer_rewarded == False
                    )
                ).order_by(self.users_table.c.register_date.desc())
                
                pending_referrals = connection.execute(pending_stmt).fetchall()
                
                pending_rewards = []
                current_time = datetime.datetime.now(pytz.utc)
                
                for ref in pending_referrals:
                    ref_id, username, first_name, register_date, redeem_date = ref
                    hours_passed = (current_time - register_date).total_seconds() / 3600
                    
                    pending_rewards.append({
                        'user_id': ref_id,
                        'username': username,
                        'first_name': first_name,
                        'hours_passed': int(hours_passed),
                        'hours_left': max(0, 48 - int(hours_passed)),
                        'can_claim': hours_passed >= 48
                    })
                
                return {
                    'total': total_referrals,
                    'redeemed': redeemed_referrals,
                    'rewarded': rewards_received,
                    'pending': pending_rewards
                }
                
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка получения статистики рефералов: {e}")
            return None

    def get_users_with_pending_rewards(self):
        """
        Возвращает список user_id пользователей, у которых есть рефералы,
        готовые к получению награды
        """
        try:
            with self.engine.connect() as connection:
                # Находим всех пользователей с рефералами, которые:
                # 1. Получили настойку
                # 2. Зарегистрированы более 48 часов назад
                # 3. Еще не получили награду
                hours_48_ago = datetime.datetime.now(pytz.utc) - datetime.timedelta(hours=48)
                
                stmt = select(self.users_table.c.referrer_id.distinct()).where(
                    sa.and_(
                        self.users_table.c.referrer_id.isnot(None),
                        self.users_table.c.redeem_date.isnot(None),
                        self.users_table.c.referrer_rewarded == False,
                        self.users_table.c.register_date <= hours_48_ago
                    )
                )
                
                result = connection.execute(stmt).fetchall()
                return [row[0] for row in result]
                
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка получения пользователей с наградами: {e}")
            return []

    def get_recently_redeemed_referrals(self, hours=2):
        """
        Возвращает список рефералов, которые получили настойку в последние N часов
        """
        try:
            with self.engine.connect() as connection:
                hours_ago = datetime.datetime.now(pytz.utc) - datetime.timedelta(hours=hours)
                
                stmt = select(
                    self.users_table.c.user_id,
                    self.users_table.c.username,
                    self.users_table.c.first_name,
                    self.users_table.c.referrer_id,
                    self.users_table.c.redeem_date
                ).where(
                    sa.and_(
                        self.users_table.c.referrer_id.isnot(None),
                        self.users_table.c.redeem_date.isnot(None),
                        self.users_table.c.redeem_date >= hours_ago,
                        self.users_table.c.referrer_rewarded == False
                    )
                ).order_by(self.users_table.c.redeem_date.desc())
                
                result = connection.execute(stmt).fetchall()
                
                recent_referrals = []
                for row in result:
                    user_id, username, first_name, referrer_id, redeem_date = row
                    recent_referrals.append({
                        'user_id': user_id,
                        'username': username, 
                        'first_name': first_name,
                        'referrer_id': referrer_id,
                        'redeem_date': redeem_date
                    })
                
                return recent_referrals
                
        except Exception as e:
            logging.error(f"PostgreSQL | Ошибка получения недавних активаций рефералов: {e}")
            return []
