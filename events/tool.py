from typing import Any, Dict, List

from events.repository import event_repository
from utils.logger import get_logger
from utils.sql_parser import QuerySchema, SQLParser

logger = get_logger(__name__)

def fetch_events(query_schema: QuerySchema) -> List[Dict[str, Any]]:
    """
    Fetch event records from the database using a structured query schema.

    This function is designed to be used by an LLM agent. It accepts a QuerySchema
    object that defines what data to retrieve, how to filter it, and how to sort it.
    The schema is validated and safely converted into a parameterized SQL query.

    Capabilities:
    - Select specific columns from the "events" table
    - Apply multiple filter conditions using AND / OR logic
    - Join with other allowed tables (e.g., "users")
    - Sort results using a single column (ORDER BY)
    - Limit the number of returned rows (max limit enforced)

    Important Notes for LLM:
    - Only use tables and columns defined in the allowed schema
    - Filters are combined using the "filter_operator" field ("AND" or "OR")
    - Use "LIKE" operator for partial text matching (e.g., "%music%")
    - Column names can be provided as "column" or "table.column"
    - Keep queries simple; nested conditions are not supported
    - Avoid requesting unnecessary columns to reduce data size

    Args:
        query_schema (QuerySchema):
            Structured query definition containing:
            - table: Main table to query (typically "events")
            - columns: List of columns to return
            - filters: List of filter conditions
            - filter_operator: Logical operator to combine filters ("AND"/"OR")
            - joins: Optional joins with other tables
            - order_by: Optional sorting configuration
            - limit: Maximum number of results to return

    Returns:
        List[Dict[str, Any]]:
            A list of event records, where each record is a dictionary
            mapping column names to their corresponding values.

    Raises:
        Exception:
            If query validation fails or database execution encounters an error.
    """
    try:
        query, params = SQLParser.generate_valid_sql(query_schema=query_schema)

        events = event_repository.execute_query(query=query,params=params,fetch_all=True)
        return events
    except Exception as e:
        logger.exception("Failed to execute search")
        raise e
