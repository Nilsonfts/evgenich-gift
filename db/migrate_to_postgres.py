"""
Скрипт для миграции данных из SQLite в PostgreSQL.
"""
import sqlite3
import logging
import os
import datetime
import pytz

from config import DATABASE_PATH, USE_POSTGRES, DATABASE_URL
from db.postgres_client import PostgresClient

def migrate_sqlite_to_postgres():
    """
    Мигрирует данные из SQLite в PostgreSQL.
    
    Returns:
        bool: True если миграция успешна, False в случае ошибки
    """
    if not os.path.exists(DATABASE_PATH):
        logging.error(f"SQLite database not found at {DATABASE_PATH}")
        return False
    
    try:
        # Подключаемся к SQLite
        sqlite_conn = sqlite3.connect(DATABASE_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Инициализируем PostgreSQL клиент
        pg_client = PostgresClient()
        
        # Создаем таблицы в PostgreSQL
        if not pg_client.create_tables():
            logging.error("Failed to create tables in PostgreSQL")
            return False
        
        # Мигрируем пользователей
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        migrated_users = 0
        
        for user in users:
            user_dict = dict(user)
            
            # Преобразуем строковые даты в datetime
            register_date = datetime.datetime.fromisoformat(user_dict['register_date']) if user_dict['register_date'] else datetime.datetime.now(pytz.timezone('Europe/Moscow'))
            last_activity = datetime.datetime.fromisoformat(user_dict['last_activity']) if user_dict['last_activity'] else datetime.datetime.now(pytz.timezone('Europe/Moscow'))
            
            # Добавляем пользователя в PostgreSQL
            with pg_client.engine.connect() as connection:
                stmt = pg_client.users_table.insert().values(
                    user_id=user_dict['user_id'],
                    username=user_dict['username'],
                    first_name=user_dict['first_name'],
                    status=user_dict['status'],
                    register_date=register_date,
                    last_activity=last_activity,
                    source=user_dict['source'],
                    referrer_id=user_dict['referrer_id'],
                    brought_by_staff_id=user_dict.get('brought_by_staff_id')
                )
                connection.execute(stmt)
                connection.commit()
                migrated_users += 1
        
        logging.info(f"Migrated {migrated_users} users to PostgreSQL")
        
        # Мигрируем сотрудников
        sqlite_cursor.execute("SELECT * FROM staff")
        staff_members = sqlite_cursor.fetchall()
        migrated_staff = 0
        
        for staff in staff_members:
            staff_dict = dict(staff)
            
            with pg_client.engine.connect() as connection:
                stmt = pg_client.staff_table.insert().values(
                    telegram_id=staff_dict['telegram_id'],
                    full_name=staff_dict['full_name'],
                    position=staff_dict['position'],
                    status=staff_dict['status']
                )
                connection.execute(stmt)
                connection.commit()
                migrated_staff += 1
        
        logging.info(f"Migrated {migrated_staff} staff members to PostgreSQL")
        
        # Мигрируем бронирования
        sqlite_cursor.execute("SELECT * FROM bookings")
        bookings = sqlite_cursor.fetchall()
        migrated_bookings = 0
        
        for booking in bookings:
            booking_dict = dict(booking)
            
            # Преобразуем строковые даты в datetime
            date = datetime.datetime.fromisoformat(booking_dict['date']) if booking_dict['date'] else None
            created = datetime.datetime.fromisoformat(booking_dict['created']) if booking_dict['created'] else datetime.datetime.now(pytz.timezone('Europe/Moscow'))
            
            with pg_client.engine.connect() as connection:
                stmt = pg_client.bookings_table.insert().values(
                    user_id=booking_dict['user_id'],
                    date=date,
                    time=booking_dict['time'],
                    guests=booking_dict['guests'],
                    name=booking_dict['name'],
                    phone=booking_dict['phone'],
                    comment=booking_dict['comment'],
                    status=booking_dict['status'],
                    created=created,
                    source=booking_dict.get('source', 'bot'),
                    source_detail=booking_dict.get('source_detail')
                )
                connection.execute(stmt)
                connection.commit()
                migrated_bookings += 1
        
        logging.info(f"Migrated {migrated_bookings} bookings to PostgreSQL")
        
        # Мигрируем настройки
        sqlite_cursor.execute("SELECT * FROM settings")
        settings = sqlite_cursor.fetchall()
        migrated_settings = 0
        
        for setting in settings:
            setting_dict = dict(setting)
            
            # Преобразуем строковую дату в datetime
            updated = datetime.datetime.fromisoformat(setting_dict['updated']) if setting_dict['updated'] else datetime.datetime.now(pytz.timezone('Europe/Moscow'))
            
            with pg_client.engine.connect() as connection:
                stmt = pg_client.settings_table.insert().values(
                    key=setting_dict['key'],
                    value=setting_dict['value'],
                    updated=updated
                )
                connection.execute(stmt)
                connection.commit()
                migrated_settings += 1
        
        logging.info(f"Migrated {migrated_settings} settings to PostgreSQL")
        
        # Мигрируем события
        sqlite_cursor.execute("SELECT * FROM events")
        events = sqlite_cursor.fetchall()
        migrated_events = 0
        
        for event in events:
            event_dict = dict(event)
            
            # Преобразуем строковую дату в datetime
            timestamp = datetime.datetime.fromisoformat(event_dict['timestamp']) if event_dict['timestamp'] else datetime.datetime.now(pytz.timezone('Europe/Moscow'))
            
            with pg_client.engine.connect() as connection:
                stmt = pg_client.events_table.insert().values(
                    user_id=event_dict['user_id'],
                    event_type=event_dict['event_type'],
                    event_data=event_dict['event_data'],
                    timestamp=timestamp
                )
                connection.execute(stmt)
                connection.commit()
                migrated_events += 1
        
        logging.info(f"Migrated {migrated_events} events to PostgreSQL")
        
        # Мигрируем результаты игр
        sqlite_cursor.execute("SELECT * FROM game_results")
        game_results = sqlite_cursor.fetchall()
        migrated_game_results = 0
        
        for result in game_results:
            result_dict = dict(result)
            
            # Преобразуем строковую дату в datetime
            timestamp = datetime.datetime.fromisoformat(result_dict['timestamp']) if result_dict['timestamp'] else datetime.datetime.now(pytz.timezone('Europe/Moscow'))
            
            with pg_client.engine.connect() as connection:
                stmt = pg_client.game_results_table.insert().values(
                    user_id=result_dict['user_id'],
                    game_type=result_dict['game_type'],
                    result=result_dict['result'],
                    points=result_dict['points'],
                    timestamp=timestamp
                )
                connection.execute(stmt)
                connection.commit()
                migrated_game_results += 1
        
        logging.info(f"Migrated {migrated_game_results} game results to PostgreSQL")
        
        # Закрываем соединения
        sqlite_conn.close()
        
        logging.info("Migration from SQLite to PostgreSQL completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if USE_POSTGRES and DATABASE_URL:
        logging.info("Starting migration from SQLite to PostgreSQL...")
        success = migrate_sqlite_to_postgres()
        
        if success:
            logging.info("Migration completed successfully!")
        else:
            logging.error("Migration failed!")
    else:
        logging.error("PostgreSQL is not enabled or DATABASE_URL is not set")
