from __future__ import annotations

import re
import sqlite3
from typing import Any

from context import DB_PATH
from logger import get_logger

logger = get_logger(__name__)

MAX_ROWS = 500

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b",
    re.IGNORECASE,
)


def _normalize_query(query: str) -> str:
    return query.strip().rstrip(";")


def validate_query(query: str) -> str | None:
    normalized = _normalize_query(query)

    if not normalized:
        return "Query is empty."

    # if not normalized.upper().startswith("SELECT"):
    #     return "Only SELECT queries are allowed."

    if FORBIDDEN_KEYWORDS.search(normalized):
        return "Query contains forbidden SQL keywords."

    if ";" in normalized:
        return "Multiple SQL statements are not allowed."

    return None


def _ensure_limit(query: str, max_rows: int = MAX_ROWS) -> str:
    if re.search(r"\bLIMIT\b", query, re.IGNORECASE):
        return query
    return f"{query} LIMIT {max_rows}"


def execute_readonly_sql(query: str) -> dict[str, Any]:
    normalized = _normalize_query(query)

    error = validate_query(normalized)
    if error:
        logger.warning(f"Rejected SQL query: {normalized} | reason={error}")
        return {"error": error}

    if not DB_PATH.is_file():
        return {"error": "Database file not found. Run datasets.py to sync data first."}

    safe_query = _ensure_limit(normalized)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(safe_query).fetchall()
            result_rows = [dict(row) for row in rows]
            columns = list(result_rows[0].keys()) if result_rows else []

            logger.info(f"SQL executed successfully | rows={len(result_rows)}")

            return {
                "row_count": len(result_rows),
                "columns": columns,
                "rows": result_rows,
            }

    except sqlite3.Error as exc:
        logger.error(f"SQL execution failed: {exc} | query={safe_query}", exc_info=True)
        return {"error": f"Query failed: {exc}"}
