import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "library_system")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin1234")

SQL = """
UPDATE app_user
SET role_id = 1
WHERE email = %s;

SELECT user_id, email, role_id
FROM app_user
ORDER BY user_id;
"""

def main():
    email_to_make_admin = "admin2@library.com"

    print("Kapcsolódás:", DB_HOST, DB_PORT, DB_NAME, DB_USER)
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SQL, (email_to_make_admin,))
            conn.commit()

            rows = cur.fetchall()
            print("=== app_user lista (user_id,email,role_id) ===")
            for r in rows:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
