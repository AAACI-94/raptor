"""SQLite database with WAL mode. Schema migration on startup."""

import logging
import sqlite3
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_connection: sqlite3.Connection | None = None

SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


def get_db() -> sqlite3.Connection:
    """Get the database connection. Creates one if it doesn't exist."""
    global _connection
    if _connection is None:
        _connection = _create_connection()
    return _connection


def _create_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with WAL mode and optimal settings."""
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")

    logger.info("[database] Connected to %s (WAL mode)", db_path)
    return conn


def init_db() -> None:
    """Run schema migration on startup."""
    conn = get_db()
    if SCHEMA_PATH.exists():
        schema = SCHEMA_PATH.read_text()
        conn.executescript(schema)
        conn.commit()
        logger.info("[database] Schema applied from %s", SCHEMA_PATH)
    else:
        logger.warning("[database] Schema file not found at %s", SCHEMA_PATH)


def close_db() -> None:
    """Close the database connection with WAL checkpoint."""
    global _connection
    if _connection is not None:
        try:
            _connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception as e:
            logger.debug("[database] WAL checkpoint on close failed: %s", e)
        _connection.close()
        _connection = None
        logger.info("[database] Connection closed")


def safe_update(table: str, updates: dict, where_col: str, where_val: str, allowed_columns: set[str]) -> None:
    """Execute a safe UPDATE with column allowlist validation."""
    filtered = {k: v for k, v in updates.items() if k in allowed_columns}
    if not filtered:
        return
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [where_val]
    conn = get_db()
    conn.execute(f"UPDATE {table} SET {set_clause} WHERE {where_col} = ?", values)
    conn.commit()


def check_db() -> bool:
    """Health check: verify database is accessible."""
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.debug("[database] Health check failed: %s", e)
        return False
