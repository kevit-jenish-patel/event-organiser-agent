from typing import Any, Dict, List, Literal, Optional, Tuple, Type

from pydantic import BaseModel, Field, ValidationError
from sqlglot import exp

from utils.constants import MAX_LIMIT
from utils.logger import get_logger

logger = get_logger(__name__)

class Filter(BaseModel):
    field: str = Field(
        ...,
        description="Column name to apply the filter on. Always use 'table_name.column_name'. Must exist in allowed schema."
    )
    operator: Literal["=", ">", "<", ">=", "<=", "LIKE"] = Field(
        ...,
        description="Comparison operator to use for filtering. Supported operators: '=', '>', '<', '>=', '<=', 'LIKE'."
    )
    value: Any = Field(
        ...,
        description="Value to compare the column against. This will be passed as a parameterized value in the SQL query."
    )


class Join(BaseModel):
    table: str = Field(
        ...,
        description="Name of the table to join with. Must exist in the allowed schema."
    )
    left_field: str = Field(
        ...,
        description="Column from the base table used in the join condition. Format: 'column' or 'table.column'."
    )
    right_field: str = Field(
        ...,
        description="Column from the join table used in the join condition. Format: 'column' or 'table.column'."
    )
    join_type: Literal["INNER", "LEFT"] = Field(
        default="INNER",
        description="Type of SQL join. Supported values: 'INNER' (default), 'LEFT'."
    )


class OrderBy(BaseModel):
    field: str = Field(
        ...,
        description="Column to sort the results by. Always use 'table_name.column_name'. Must exist in allowed schema."
    )
    direction: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort direction: 'asc' for ascending (default) or 'desc' for descending."
    )


class QuerySchema(BaseModel):
    table: str = Field(
        ...,
        description="Main table to query data from. Must exist in the allowed schema."
    )

    columns: List[str] = Field(
        ...,
        description="List of columns to include in the SELECT clause. Always use table_name.column_name. Each column must exist in the allowed schema."
    )

    filters: Optional[List[Filter]] = Field(
        default_factory=list,
        description="List of filter conditions to apply in the WHERE clause. All conditions are combined using 'filter_operator'."
    )

    filter_operator: Literal["AND", "OR"] = Field(
        default="AND",
        description="Logical operator used to combine all filter conditions. 'AND' means all conditions must match, 'OR' means any condition can match."
    )

    joins: Optional[List[Join]] = Field(
        default_factory=list,
        description="List of join operations to perform. Each join defines how another table is connected to the main table."
    )

    limit: Optional[int] = Field(
        default=10,
        le=MAX_LIMIT,
        description="Maximum number of rows to return. Must not exceed system-defined limit."
    )

    order_by: Optional[OrderBy] = Field(
        default=None,
        description="Optional sorting configuration to order the query results."
    )


class SQLParser:
    ALLOWED_SCHEMA = {
        "events": ["id", "name", "description", "date", "location", "organiser_id", "status"],
        "users": ["id", "name", "email"]
    }

    OPERATOR_MAP: Dict[str, Type[exp.Expression]] = {
        "=": exp.EQ,
        ">": exp.GT,
        "<": exp.LT,
        ">=": exp.GTE,
        "<=": exp.LTE,
        "LIKE": exp.Like,
    }

    @classmethod
    def build_sql_from_schema(cls, query_schema: QuerySchema) -> Tuple[str, Tuple[Any]]:
        params: List[Any] = []

        columns = []
        for col in query_schema.columns:
            if "." in col:
                table, column = col.split(".", 1)
                columns.append(exp.column(column, table=table))
            else:
                columns.append(exp.column(col))

        query = exp.select(*columns).from_(
            exp.Table(this=query_schema.table)
        )

        query = cls._apply_joins(query, query_schema.joins)
        query = cls._apply_filters(query, query_schema, params)
        query = cls._apply_order_by(query, query_schema.order_by)
        query = query.limit(query_schema.limit)

        return query.sql(), tuple(params)

    @classmethod
    def _apply_joins(cls, query, joins: List[Join]):
        for join in joins:
            query = query.join(
                exp.Join(
                    this=exp.Table(this=join.table),
                    on=exp.condition(f"{join.left_field} = {join.right_field}"),
                    join_type=join.join_type.lower(),
                )
            )
        return query

    @classmethod
    def _apply_filters(cls, query, query_schema: QuerySchema, params: List[Any]):
        if not query_schema.filters:
            return query

        conditions = []

        for f in query_schema.filters:
            params.append(f.value)

            column = exp.column(f.field)
            operator_cls = cls.OPERATOR_MAP[f.operator]

            condition = operator_cls(
                this=column,
                expression=exp.Var(this="?")
            )

            conditions.append(condition)

        where_expr = conditions[0]
        combiner = exp.and_ if query_schema.filter_operator == "AND" else exp.or_

        for cond in conditions[1:]:
            where_expr = combiner(where_expr, cond)

        return query.where(where_expr)

    @classmethod
    def _apply_order_by(cls, query, order_by: Optional[OrderBy]):
        if not order_by:
            return query

        column = exp.column(order_by.field)
        order_expr = column.asc() if order_by.direction == "asc" else column.desc()

        return query.order_by(order_expr)

    @classmethod
    def _validate_column(cls,column: str, base_table:str,is_select_column: bool = False) -> None:
        if "." in column:
            table, col = column.split(".", 1)
        else:
            table, col = None, column

        if table:
            if table not in cls.ALLOWED_SCHEMA:
                raise ValidationError(f"Invalid table in column: {column}")
            if col not in cls.ALLOWED_SCHEMA[table]:
                raise ValidationError(f"Invalid column: {column}")
        else:
            # fallback to main table
            if base_table not in cls.ALLOWED_SCHEMA:
                raise ValidationError(f"Invalid base table: {base_table}")
            if col not in cls.ALLOWED_SCHEMA[base_table]:
                raise ValidationError(f"Invalid column: {column}")

        if is_select_column and col in {"id"}:
            raise ValidationError(f"Invalid column: {column}")

    @classmethod
    def _validate_filter_schema(cls, filter_schema: Filter, base_table: str) -> None:
        if filter_schema.operator not in cls.OPERATOR_MAP:
            raise ValidationError(f"Invalid operator: {filter_schema.operator}")

        cls._validate_column(column=filter_schema.field, base_table=base_table)

    @classmethod
    def _validate_join_schema(cls, join_schema: Join, base_table:str) -> None:
        if join_schema.table not in cls.ALLOWED_SCHEMA:
            raise ValidationError(f"Invalid join table: {join_schema.table}")

        cls._validate_column(column=join_schema.left_field, base_table=base_table)
        cls._validate_column(column=join_schema.right_field, base_table=join_schema.table)

    @classmethod
    def validate_schema(cls, query_schema: QuerySchema) -> QuerySchema:
        try:
            query_schema = QuerySchema.model_validate(query_schema)

            if query_schema.table not in cls.ALLOWED_SCHEMA:
                raise ValidationError(f"Invalid table: {query_schema.table}")

            if not query_schema.columns:
                raise ValidationError("No select columns specified")

            for col in query_schema.columns:
                cls._validate_column(column=col, base_table=query_schema.table,is_select_column=True)

            for filter_schema in query_schema.filters or []:
                cls._validate_filter_schema(filter_schema=filter_schema,base_table=query_schema.table)

            for join_schema in query_schema.joins or []:
                cls._validate_join_schema(join_schema=join_schema, base_table=query_schema.table)

            if query_schema.order_by:
                cls._validate_column(column=query_schema.order_by.field, base_table=query_schema.table)

            return query_schema
        except ValidationError as e:
            logger.exception(f"Invalid query schema \n{query_schema}\n")
            raise e

    @classmethod
    def generate_valid_sql(cls, query_schema: QuerySchema) -> Tuple[str, Tuple[Any]]:
        try:
            query_schema = cls.validate_schema(query_schema=query_schema)

            sql, params = cls.build_sql_from_schema(query_schema=query_schema)
            return sql, params
        except Exception as e:
            logger.exception("Failed to generate SQL from schema")
            raise e
