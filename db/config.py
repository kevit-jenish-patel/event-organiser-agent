import sqlite3
from typing import Optional

from core.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SQLiteManager:
    _connection: Optional[sqlite3.Connection] = None

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        if cls._connection is None:
            try:
                cls._connection = sqlite3.connect(
                    settings.SQLITE_DB_PATH,  # e.g. "test.db"
                    check_same_thread=False  # useful for multi-thread apps
                )
                cls._connection.row_factory = sqlite3.Row  # dict-like rows
            except Exception:
                logger.exception("Failed to create SQLite connection")
                raise
        return cls._connection

    @classmethod
    def get_db(cls) -> sqlite3.Connection:
        try:
            return cls._get_connection()
        except Exception:
            logger.exception("Failed to get SQLite database connection")
            raise

    @classmethod
    def close(cls):
        if cls._connection:
            cls._connection.close()
            cls._connection = None

    @classmethod
    def init_db(cls):
        db = cls.get_db()
        db.execute("PRAGMA foreign_keys = ON")
        cursor = db.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                location TEXT NOT NULL,
                organiser_id INTEGER NOT NULL,
                status TEXT DEFAULT 'OPEN',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (organiser_id) REFERENCES users(id)
            );
            """
        )

        db.commit()
