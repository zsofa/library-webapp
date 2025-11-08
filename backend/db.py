import logging
import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor


def get_db_connection() -> PGConnection:
    """
    Create a psycopg2 connection using environment variables from .env.
    Sets the session time zone to UTC to ensure consistent timestamp handling.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "library"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )

    # Ensure session uses UTC for timestamp fields
    try:
        original_autocommit = conn.autocommit
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC'")
    except Exception:
        logging.exception("Failed to set session time zone to UTC")
    finally:
        # Restore original autocommit mode
        try:
            conn.autocommit = original_autocommit
        except Exception:
            pass

    return conn


@contextmanager
def get_db_cursor(commit: bool = False) -> Iterator[RealDictCursor]:
    """
    Context manager that yields a cursor and closes the connection afterwards.

    If commit=True:
      - commit on success
      - rollback on exception
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        logging.exception("Database error")
        raise
    finally:
        conn.close()
