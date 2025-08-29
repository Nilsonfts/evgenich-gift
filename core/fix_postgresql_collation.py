#!/usr/bin/env python3
"""
Скрипт для исправления предупреждений PostgreSQL о несоответствии версий collation.
Выполняет команду ALTER DATABASE railway REFRESH COLLATION VERSION.
"""
import os
import sys
import logging
import psycopg2
from psycopg2 import sql

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import POSTGRES_URL

#!/usr/bin/env python3
"""
Скрипт для исправления проблем с PostgreSQL collation.
Выполняется автоматически при старте приложения.
"""

import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def fix_postgresql_collation():
    """Исправляет проблемы с collation в PostgreSQL."""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logging.warning("DATABASE_URL не установлен, пропускаем исправление collation")
        return False
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Проверяем текущую версию collation
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()
            logging.info(f"PostgreSQL версия: {version[:100]}...")
            
            # Выполняем обновление collation
            try:
                connection.execute(text("ALTER DATABASE railway REFRESH COLLATION VERSION"))
                connection.commit()
                logging.info("✅ PostgreSQL collation version успешно обновлена")
                return True
            except SQLAlchemyError as e:
                if "already up to date" in str(e).lower():
                    logging.info("✅ PostgreSQL collation уже актуальна")
                    return True
                else:
                    logging.warning(f"⚠️  Не удалось обновить collation (не критично): {e}")
                    return False
                    
    except Exception as e:
        logging.error(f"❌ Ошибка при исправлении PostgreSQL collation: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fix_postgresql_collation()
