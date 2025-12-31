from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

from flask import Blueprint, Response, jsonify, request
from psycopg2.errors import UniqueViolation

from auth_utils import role_required
from config import DEFAULT_LOAN_DAYS
from db import get_db_cursor
from parse_utils import ParseError, parse_int
from response_utils import error_response

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin/stats")
@role_required("admin")
def get_stats() -> Tuple[Response, int]:
    sql = """
        SELECT
            (SELECT COUNT(*) FROM App_User) AS total_users,
            (SELECT COUNT(*) FROM App_User WHERE is_active = TRUE) AS active_users,
            (SELECT COUNT(*) FROM Book) AS total_books,
            (SELECT COUNT(*) FROM Item) AS total_items,
            (SELECT COUNT(*) FROM Loan WHERE return_date IS NULL) AS active_loans,
            (
                SELECT COUNT(*)
                FROM Loan
                WHERE return_date IS NULL
                  AND due_date < CURRENT_DATE
            ) AS overdue_loans,
            (SELECT COUNT(*) FROM Reservation) AS total_reservations
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql)
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("db_error", "Statistics query returned no data.", status=500)

    return (
        jsonify(
            {
                "total_users": int(row["total_users"]),
                "active_users": int(row["active_users"]),
                "total_books": int(row["total_books"]),
                "total_items": int(row["total_items"]),
                "active_loans": int(row["active_loans"]),
                "overdue_loans": int(row["overdue_loans"]),
                "total_reservations": int(row["total_reservations"]),
            }
        ),
        200,
    )


@admin_bp.get("/admin/waitlist")
@role_required("admin")
def admin_waitlist() -> Tuple[Response, int]:
    q = (request.args.get("q") or "").strip()
    waiting_only = (request.args.get("waiting_only") or "true").strip().lower() == "true"
    limit_raw = (request.args.get("limit") or "200").strip()

    try:
        limit = parse_int(limit_raw, field="limit", error_code="invalid_limit", message="limit must be an integer.")
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    if limit <= 0:
        return error_response("invalid_limit", "limit must be positive.", status=400)
    if limit > 500:
        limit = 500

    where = []
    params = []

    if waiting_only:
        where.append("r.status IN ('pending', 'ready')")

    if q:
        q_like = f"%{q.lower()}%"
        where.append(
            """
            (
              LOWER(b.title) LIKE %s OR LOWER(b.author) LIKE %s
              OR LOWER(u.name) LIKE %s OR LOWER(u.email) LIKE %s
              OR CAST(r.reservation_id AS TEXT) = %s
              OR CAST(r.book_id AS TEXT) = %s
              OR CAST(r.user_id AS TEXT) = %s
            )
            """
        )
        params.extend([q_like, q_like, q_like, q_like, q, q, q])

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    sql = f"""
      SELECT
        r.reservation_id,
        r.book_id,
        b.title,
        b.author,
        r.user_id,
        u.name AS user_name,
        u.email AS user_email,
        r.queue_number,
        r.reservation_date,
        r.expiry_date,
        r.status,
        (
          (SELECT COUNT(*) FROM Item i WHERE i.book_id = r.book_id)
          -
          (SELECT COUNT(*)
             FROM Loan l
             JOIN Item i2 ON i2.item_id = l.item_id
            WHERE i2.book_id = r.book_id
              AND l.return_date IS NULL
          )
        ) AS available_items
      FROM Reservation r
      JOIN Book b ON b.book_id = r.book_id
      JOIN App_User u ON u.user_id = r.user_id
      {where_sql}
      ORDER BY r.book_id ASC, r.queue_number ASC
      LIMIT %s
    """
    params.append(limit)

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall() or []
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    result = []
    for r in rows:
        avail = int(r["available_items"] or 0)
        status = (r["status"] or "").lower()
        can_borrow = avail > 0 and status in ("pending", "ready")

        result.append(
            {
                "reservation_id": r["reservation_id"],
                "book_id": r["book_id"],
                "title": r["title"],
                "author": r["author"],
                "user_id": r["user_id"],
                "user_name": r["user_name"],
                "user_email": r["user_email"],
                "queue_number": r["queue_number"],
                "reservation_date": r["reservation_date"].isoformat() if r["reservation_date"] else None,
                "expiry_date": r["expiry_date"].isoformat() if r["expiry_date"] else None,
                "status": r["status"],
                "available_items": avail,
                "canBorrow": can_borrow,
            }
        )

    return jsonify(result), 200


def _pick_available_item_for_book(cur, book_id: int) -> Optional[dict]:
    """
    Pick one free item for the book (global), concurrency-safe.
    """
    sql = """
      SELECT i.item_id, i.book_id, i.library_id
      FROM Item i
      WHERE i.book_id = %s
        AND NOT EXISTS (
          SELECT 1 FROM Loan l
          WHERE l.item_id = i.item_id
            AND l.return_date IS NULL
        )
      ORDER BY i.item_id ASC
      FOR UPDATE SKIP LOCKED
      LIMIT 1
    """
    cur.execute(sql, (book_id,))
    return cur.fetchone()


@admin_bp.post("/admin/issue_next")
@role_required("admin")
def issue_next() -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}

    if "book_id" not in data:
        return error_response("missing_fields", "Missing required field: book_id.", status=400)

    try:
        book_id = parse_int(
            data.get("book_id"),
            field="book_id",
            error_code="invalid_ids",
            message="book_id must be an integer.",
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    loan_days_raw = data.get("loan_days")
    try:
        loan_days = (
            parse_int(
                loan_days_raw,
                field="loan_days",
                error_code="invalid_loan_days",
                message="loan_days must be an integer.",
            )
            if loan_days_raw is not None
            else DEFAULT_LOAN_DAYS
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    if loan_days <= 0:
        return error_response("invalid_loan_days", "loan_days must be positive.", status=400)

    now = datetime.now(timezone.utc)
    due_date = (now + timedelta(days=loan_days)).date()

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT reservation_id, user_id, book_id, queue_number, status
                FROM Reservation
                WHERE book_id = %s
                  AND status IN ('pending', 'ready')
                ORDER BY queue_number ASC
                LIMIT 1
                FOR UPDATE
                """,
                (book_id,),
            )
            res = cur.fetchone()
            if res is None:
                return error_response(
                    "no_waitlist",
                    "No pending/ready reservation for this book.",
                    status=409,
                )

            chosen_item = _pick_available_item_for_book(cur, book_id)
            if chosen_item is None:
                return error_response(
                    "no_available_item",
                    "No available item for this book.",
                    status=409,
                )

            cur.execute(
                """
                INSERT INTO Loan (item_id, user_id, loan_date, due_date, fine_paid)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING loan_id
                """,
                (chosen_item["item_id"], res["user_id"], now, due_date, 0.00),
            )
            loan_row = cur.fetchone()

            cur.execute(
                """
                UPDATE Reservation
                SET status = 'fulfilled'
                WHERE reservation_id = %s
                """,
                (res["reservation_id"],),
            )

    except UniqueViolation:
        return error_response("conflict", "Conflict occurred.", status=409)
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return (
        jsonify(
            {
                "reservation_id": res["reservation_id"],
                "book_id": book_id,
                "user_id": res["user_id"],
                "loan_id": loan_row["loan_id"] if loan_row else None,
                "item_id": chosen_item["item_id"],
                "due_date": due_date.isoformat(),
            }
        ),
        200,
    )
