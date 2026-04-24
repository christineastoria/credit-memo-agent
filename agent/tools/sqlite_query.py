"""
SQLite query tool for accessing internal deal and portfolio data.

Provides natural-language-to-SQL query capability against the deals.db
database. The agent describes what data it needs, and this tool translates
that into SQL and returns the results.

Tables available:
  - deals: Historical deal records (borrower, type, spread, leverage, outcome)
  - portfolio: Current holdings (borrower, instrument, price, yield, risk rating)
"""

import os
import sqlite3

from langchain.tools import tool

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "deals.db")


def _get_schema() -> str:
    """Return the database schema as a string for context."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schemas = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return "\n\n".join(schemas)


def _execute_query(sql: str) -> str:
    """Execute a SQL query and return formatted results."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()

        if not rows:
            return "Query returned no results."

        # Format as a readable table with column headers
        columns = rows[0].keys()
        header = " | ".join(columns)
        separator = "-|-".join("-" * len(col) for col in columns)
        data_rows = []
        for row in rows:
            data_rows.append(" | ".join(str(row[col]) for col in columns))

        return f"{header}\n{separator}\n" + "\n".join(data_rows)

    except sqlite3.Error as e:
        return f"SQL Error: {e}"
    finally:
        conn.close()


@tool
def query_deals_db(sql_query: str) -> str:
    """Execute a SQL query against the internal deals database.

    The database has two tables:

    deals: Historical deal records
      - borrower, deal_type, deal_date, amount_mm, spread_bps,
        leverage_at_close, sector, rating, outcome

    portfolio: Current portfolio holdings
      - borrower, instrument, par_amount_mm, current_price,
        yield_pct, sector, maturity_date, risk_rating

    Write a SELECT query to retrieve the data you need.
    Only SELECT queries are allowed.
    """
    # Safety check — only allow read operations
    normalized = sql_query.strip().upper()
    if not normalized.startswith("SELECT"):
        return "Error: Only SELECT queries are allowed for safety."

    dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]
    for keyword in dangerous_keywords:
        if keyword in normalized:
            return f"Error: {keyword} operations are not allowed."

    return _execute_query(sql_query)


@tool
def get_db_schema() -> str:
    """Get the database schema for the internal deals database.
    Use this to understand available tables and columns before writing queries.
    """
    return _get_schema()
