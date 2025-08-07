"""
Модуль для работы с двойной системой баз данных (PostgreSQL и SQLite).
"""
import logging
import psycopg2
import sqlite3
from datetime import datetime

class DualDatabase:
    """
    Класс для работы с двумя базами данных одновременно:
    1. PostgreSQL - основная база данных на сервере
    2. SQLite - локальная база данных
    """
    
    def __init__(self, pg_url, sqlite_path):
        """
        Инициализация подключений к базам данных
        
        Args:
            pg_url (str): URL для подключения к PostgreSQL
            sqlite_path (str): Путь к файлу базы данных SQLite
        """
        self.pg_url = pg_url
        self.sqlite_path = sqlite_path
        self.logger = logging.getLogger(__name__)
        
        # Настройка логирования, если не настроено
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        # Проверка подключений
        try:
            self._check_pg_connection()
            self.logger.info("Подключение к PostgreSQL установлено")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        
        try:
            self._check_sqlite_connection()
            self.logger.info("Подключение к SQLite установлено")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к SQLite: {e}")
    
    def _check_pg_connection(self):
        """Проверяет соединение с PostgreSQL"""
        conn = psycopg2.connect(self.pg_url)
        conn.close()
        return True
    
    def _check_sqlite_connection(self):
        """Проверяет соединение с SQLite"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.close()
        return True
    
    def add_user(self, user_data):
        """
        Добавляет пользователя в обе базы данных
        
        Args:
            user_data (dict): Данные пользователя
            
        Returns:
            bool: True, если пользователь добавлен хотя бы в одну базу, иначе False
        """
        pg_result = self._add_user_to_postgres(user_data)
        sqlite_result = self._add_user_to_sqlite(user_data)
        
        return pg_result or sqlite_result
    
    def _add_user_to_postgres(self, user_data):
        """
        Добавляет пользователя в PostgreSQL базу
        
        Args:
            user_data (dict): Данные пользователя
            
        Returns:
            bool: True, если операция успешна, иначе False
        """
        try:
            # Подключение к PostgreSQL
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            # SQL запрос для добавления пользователя
            insert_query = """
            INSERT INTO users (
                user_id, username, first_name, status, phone_number, real_name, 
                birth_date, register_date, last_activity, redeem_date, source,
                referrer_id, brought_by_staff_id, profile_completed, ai_concept
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (user_id) DO NOTHING;
            """
            
            # Выполнение запроса
            cursor.execute(insert_query, (
                user_data.get("user_id"),
                user_data.get("username"),
                user_data.get("first_name"),
                user_data.get("status", "registered"),
                user_data.get("phone_number"),
                user_data.get("real_name"),
                user_data.get("birth_date"),
                user_data.get("register_date", datetime.now()),
                user_data.get("last_activity", datetime.now()),
                user_data.get("redeem_date"),
                user_data.get("source"),
                user_data.get("referrer_id"),
                user_data.get("brought_by_staff_id"),
                user_data.get("profile_completed", False),
                user_data.get("ai_concept", "evgenich")
            ))
            
            # Подтверждение транзакции
            conn.commit()
            self.logger.info(f"Пользователь {user_data.get('user_id')} добавлен в PostgreSQL БД")
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении пользователя в PostgreSQL: {e}")
            return False
    
    def _add_user_to_sqlite(self, user_data):
        """
        Добавляет пользователя в SQLite базу
        
        Args:
            user_data (dict): Данные пользователя
            
        Returns:
            bool: True, если операция успешна, иначе False
        """
        try:
            # Подключение к SQLite
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # SQL запрос для добавления пользователя
            insert_query = """
            INSERT OR IGNORE INTO users (
                user_id, username, first_name, status, phone_number, real_name, 
                birth_date, register_date, last_activity, redeem_date, source,
                referrer_id, brought_by_staff_id, profile_completed, ai_concept
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
            """
            
            # Преобразование для SQLite (для профиля SQLite принимает 0/1 вместо булева)
            profile_completed = 1 if user_data.get("profile_completed", False) else 0
            
            # Выполнение запроса
            cursor.execute(insert_query, (
                user_data.get("user_id"),
                user_data.get("username"),
                user_data.get("first_name"),
                user_data.get("status", "registered"),
                user_data.get("phone_number"),
                user_data.get("real_name"),
                user_data.get("birth_date"),
                user_data.get("register_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                user_data.get("last_activity", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                user_data.get("redeem_date"),
                user_data.get("source"),
                user_data.get("referrer_id"),
                user_data.get("brought_by_staff_id"),
                profile_completed,
                user_data.get("ai_concept", "evgenich")
            ))
            
            # Подтверждение транзакции
            conn.commit()
            self.logger.info(f"Пользователь {user_data.get('user_id')} добавлен в SQLite БД")
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении пользователя в SQLite: {e}")
            return False
    
    def get_user(self, user_id):
        """
        Получает данные пользователя из обеих баз данных
        (приоритет отдаётся PostgreSQL)
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            dict: Данные пользователя или None, если пользователь не найден
        """
        # Пробуем сначала получить из PostgreSQL
        user_data = self._get_user_from_postgres(user_id)
        
        # Если в PostgreSQL не найдено, ищем в SQLite
        if not user_data:
            user_data = self._get_user_from_sqlite(user_id)
        
        return user_data
    
    def _get_user_from_postgres(self, user_id):
        """
        Получает данные пользователя из PostgreSQL
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            dict: Данные пользователя или None, если пользователь не найден
        """
        try:
            # Подключение к PostgreSQL
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            # SQL запрос для получения пользователя
            select_query = "SELECT * FROM users WHERE user_id = %s;"
            
            # Выполнение запроса
            cursor.execute(select_query, (user_id,))
            
            # Получение результатов
            row = cursor.fetchone()
            
            # Получение имен колонок
            column_names = [desc[0] for desc in cursor.description]
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            if not row:
                return None
            
            # Формирование словаря с данными пользователя
            user_data = dict(zip(column_names, row))
            
            return user_data
        except Exception as e:
            self.logger.error(f"Ошибка при получении пользователя из PostgreSQL: {e}")
            return None
    
    def _get_user_from_sqlite(self, user_id):
        """
        Получает данные пользователя из SQLite
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            dict: Данные пользователя или None, если пользователь не найден
        """
        try:
            # Подключение к SQLite
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Для получения результатов в виде словаря
            cursor = conn.cursor()
            
            # SQL запрос для получения пользователя
            select_query = "SELECT * FROM users WHERE user_id = ?;"
            
            # Выполнение запроса
            cursor.execute(select_query, (user_id,))
            
            # Получение результатов
            row = cursor.fetchone()
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            if not row:
                return None
            
            # Преобразование Row в словарь
            user_data = dict(zip(row.keys(), row))
            
            # Преобразование для profile_completed из SQLite (0/1) в булево значение
            if "profile_completed" in user_data:
                user_data["profile_completed"] = bool(user_data["profile_completed"])
            
            return user_data
        except Exception as e:
            self.logger.error(f"Ошибка при получении пользователя из SQLite: {e}")
            return None
    
    def update_user(self, user_id, update_data):
        """
        Обновляет данные пользователя в обеих базах данных
        
        Args:
            user_id (int): ID пользователя
            update_data (dict): Данные для обновления
            
        Returns:
            bool: True, если пользователь обновлен хотя бы в одной базе, иначе False
        """
        pg_result = self._update_user_in_postgres(user_id, update_data)
        sqlite_result = self._update_user_in_sqlite(user_id, update_data)
        
        return pg_result or sqlite_result
    
    def _update_user_in_postgres(self, user_id, update_data):
        """
        Обновляет данные пользователя в PostgreSQL
        
        Args:
            user_id (int): ID пользователя
            update_data (dict): Данные для обновления
            
        Returns:
            bool: True, если операция успешна, иначе False
        """
        try:
            # Если нет данных для обновления
            if not update_data:
                return False
            
            # Подключение к PostgreSQL
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            # Формирование запроса UPDATE
            update_fields = []
            update_values = []
            
            for key, value in update_data.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)
            
            # Добавляем user_id в конец значений
            update_values.append(user_id)
            
            update_query = f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE user_id = %s;
            """
            
            # Выполнение запроса
            cursor.execute(update_query, update_values)
            
            # Подтверждение транзакции
            conn.commit()
            
            # Проверка, был ли обновлен пользователь
            rows_updated = cursor.rowcount
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            if rows_updated > 0:
                self.logger.info(f"Пользователь {user_id} обновлен в PostgreSQL БД")
                return True
            else:
                self.logger.info(f"Пользователь {user_id} не найден в PostgreSQL БД")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении пользователя в PostgreSQL: {e}")
            return False
    
    def _update_user_in_sqlite(self, user_id, update_data):
        """
        Обновляет данные пользователя в SQLite
        
        Args:
            user_id (int): ID пользователя
            update_data (dict): Данные для обновления
            
        Returns:
            bool: True, если операция успешна, иначе False
        """
        try:
            # Если нет данных для обновления
            if not update_data:
                return False
            
            # Подключение к SQLite
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Копируем словарь для возможного преобразования типов
            sqlite_update_data = update_data.copy()
            
            # Преобразование для profile_completed из булева значения в SQLite (0/1)
            if "profile_completed" in sqlite_update_data:
                sqlite_update_data["profile_completed"] = 1 if sqlite_update_data["profile_completed"] else 0
            
            # Формирование запроса UPDATE
            update_fields = []
            update_values = []
            
            for key, value in sqlite_update_data.items():
                update_fields.append(f"{key} = ?")
                update_values.append(value)
            
            # Добавляем user_id в конец значений
            update_values.append(user_id)
            
            update_query = f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE user_id = ?;
            """
            
            # Выполнение запроса
            cursor.execute(update_query, update_values)
            
            # Подтверждение транзакции
            conn.commit()
            
            # Проверка, был ли обновлен пользователь
            rows_updated = cursor.rowcount
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            if rows_updated > 0:
                self.logger.info(f"Пользователь {user_id} обновлен в SQLite БД")
                return True
            else:
                self.logger.info(f"Пользователь {user_id} не найден в SQLite БД")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении пользователя в SQLite: {e}")
            return False
    
    def delete_user(self, user_id):
        """
        Удаляет пользователя из обеих баз данных
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True, если пользователь удален хотя бы из одной базы, иначе False
        """
        pg_result = self._delete_user_from_postgres(user_id)
        sqlite_result = self._delete_user_from_sqlite(user_id)
        
        return pg_result or sqlite_result
    
    def _delete_user_from_postgres(self, user_id):
        """
        Удаляет пользователя из PostgreSQL
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True, если операция успешна, иначе False
        """
        try:
            # Подключение к PostgreSQL
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            # SQL запрос для удаления пользователя
            delete_query = "DELETE FROM users WHERE user_id = %s;"
            
            # Выполнение запроса
            cursor.execute(delete_query, (user_id,))
            
            # Подтверждение транзакции
            conn.commit()
            
            # Проверка, был ли удален пользователь
            rows_deleted = cursor.rowcount
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            if rows_deleted > 0:
                self.logger.info(f"Пользователь {user_id} удален из PostgreSQL БД")
                return True
            else:
                self.logger.info(f"Пользователь {user_id} не найден в PostgreSQL БД")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при удалении пользователя из PostgreSQL: {e}")
            return False
    
    def _delete_user_from_sqlite(self, user_id):
        """
        Удаляет пользователя из SQLite
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True, если операция успешна, иначе False
        """
        try:
            # Подключение к SQLite
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # SQL запрос для удаления пользователя
            delete_query = "DELETE FROM users WHERE user_id = ?;"
            
            # Выполнение запроса
            cursor.execute(delete_query, (user_id,))
            
            # Подтверждение транзакции
            conn.commit()
            
            # Проверка, был ли удален пользователь
            rows_deleted = cursor.rowcount
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            if rows_deleted > 0:
                self.logger.info(f"Пользователь {user_id} удален из SQLite БД")
                return True
            else:
                self.logger.info(f"Пользователь {user_id} не найден в SQLite БД")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при удалении пользователя из SQLite: {e}")
            return False

    def get_all_users(self, limit=None):
        """
        Получает всех пользователей из PostgreSQL (предпочтительно) или SQLite
        
        Args:
            limit (int, optional): Ограничение на количество возвращаемых пользователей
            
        Returns:
            list: Список словарей с данными пользователей
        """
        try:
            # Пробуем сначала получить из PostgreSQL
            users = self._get_all_users_from_postgres(limit)
            
            # Если в PostgreSQL не удалось, получаем из SQLite
            if users is None:
                users = self._get_all_users_from_sqlite(limit)
                
            return users if users else []
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех пользователей: {e}")
            return []
    
    def _get_all_users_from_postgres(self, limit=None):
        """
        Получает всех пользователей из PostgreSQL
        
        Args:
            limit (int, optional): Ограничение на количество возвращаемых пользователей
            
        Returns:
            list: Список словарей с данными пользователей или None в случае ошибки
        """
        try:
            # Подключение к PostgreSQL
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            # SQL запрос для получения всех пользователей
            select_query = "SELECT * FROM users"
            if limit:
                select_query += f" LIMIT {limit}"
            select_query += ";"
            
            # Выполнение запроса
            cursor.execute(select_query)
            
            # Получение результатов
            rows = cursor.fetchall()
            
            # Получение имен колонок
            column_names = [desc[0] for desc in cursor.description]
            
            # Формирование списка словарей с данными пользователей
            users = [dict(zip(column_names, row)) for row in rows]
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            return users
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех пользователей из PostgreSQL: {e}")
            return None
    
    def _get_all_users_from_sqlite(self, limit=None):
        """
        Получает всех пользователей из SQLite
        
        Args:
            limit (int, optional): Ограничение на количество возвращаемых пользователей
            
        Returns:
            list: Список словарей с данными пользователей или None в случае ошибки
        """
        try:
            # Подключение к SQLite
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Для получения результатов в виде словаря
            cursor = conn.cursor()
            
            # SQL запрос для получения всех пользователей
            select_query = "SELECT * FROM users"
            if limit:
                select_query += f" LIMIT {limit}"
            select_query += ";"
            
            # Выполнение запроса
            cursor.execute(select_query)
            
            # Получение результатов
            rows = cursor.fetchall()
            
            # Формирование списка словарей с данными пользователей
            users = [dict(row) for row in rows]
            
            # Преобразование profile_completed для всех пользователей
            for user in users:
                if "profile_completed" in user:
                    user["profile_completed"] = bool(user["profile_completed"])
            
            # Закрытие соединения
            cursor.close()
            conn.close()
            
            return users
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех пользователей из SQLite: {e}")
            return None
