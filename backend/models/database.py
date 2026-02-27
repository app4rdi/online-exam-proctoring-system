"""
Database connection and utilities
"""
import mysql.connector
from contextlib import contextmanager
from backend.config import get_config

config = get_config()

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**config.DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        raise

@contextmanager
def get_db_cursor(dictionary=True):
    """Context manager for database operations"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=dictionary)
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        cursor.close()
        if connection and connection.is_connected():
            connection.close()
