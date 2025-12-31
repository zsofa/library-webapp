from pathlib import Path
import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

from db import get_db_connection


BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR.parent / "database"

load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "library_system")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin1234")


def ensure_database():
    print(f"Connest to db as {DB_USER}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone() is not None

        if exists:
            print(f"Db already exists: {DB_NAME}")
        else:
            print(f"Db creation: {DB_NAME} ...")
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
            print("DB created.")

    conn.close()


def run_sql_file(path: Path):
    print(f"==> Running: {path}")
    conn = get_db_connection()
    with conn.cursor() as cur, open(path, encoding="utf-8") as f:
        sql = f.read()
        cur.execute(sql)
    conn.commit()
    conn.close()
    print(f"OK: {path.name}")


def main():
    print("=== DB start ===")
    ensure_database()

    table_sql = SQL_DIR / "table.sql"
    seed_sql = SQL_DIR / "seed_data.sql"

    if not table_sql.exists():
        raise FileNotFoundError(f"Can not find: {table_sql}")
    if not seed_sql.exists():
        raise FileNotFoundError(f"Can not find: {seed_sql}")

    run_sql_file(table_sql)
    run_sql_file(seed_sql)

    print("=== DONE ===")


if __name__ == "__main__":
    main()
