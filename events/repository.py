from typing import Any, Dict, List, Optional, Tuple

from db.config import SQLiteManager
from utils.logger import get_logger

logger = get_logger(__name__)


class EventRepository:
    def __init__(self):
        self.db = SQLiteManager.get_db()

    def execute_query(
        self,
        *,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        General-purpose SQLite query executor.

        Args:
            query: SQL query string
            params: Tuple of parameters for parameterized query
            fetch_one: Return single row
            fetch_all: Return all rows
            commit: Whether to commit transaction (for INSERT/UPDATE/DELETE)

        Returns:
            List[Dict] | Dict | None
        """
        try:
            cursor = self.db.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Handle SELECT
            if fetch_one:
                row = cursor.fetchone()
                return dict(row) if row else None

            if fetch_all:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            # Handle write operations
            if commit:
                self.db.commit()

            return None

        except Exception:
            logger.exception("Database query execution failed")
            raise

event_repository = EventRepository()
