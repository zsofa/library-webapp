import logging
import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor


def get_db_connection() -> PGConnection:

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "library_system"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "admin1234"),
    )

    try:
        original_autocommit = conn.autocommit
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC'")
    except Exception:
        logging.exception("Failed to set session time zone to UTC")
    finally:
        try:
            conn.autocommit = original_autocommit
        except Exception:
            pass

    return conn


@contextmanager
def get_db_cursor(commit: bool = False) -> Iterator[RealDictCursor]:
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
