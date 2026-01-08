from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, jsonify, request
from psycopg2.errors import UniqueViolation

from auth_utils import get_current_user, login_required, role_required
from config import RESERVATION_EXPIRY_DAYS, DEFAULT_LOAN_DAYS
from db import get_db_cursor
from parse_utils import ParseError, parse_int
from response_utils import error_response

reservation_bp = Blueprint("reservations", __name__)

VALID_STATUSES = {"pending", "ready", "expired", "fulfilled"}


def _serialize_reservation(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "reservation_id": row["reservation_id"],
        "book_id": row["book_id"],
        "user_id": row["user_id"],
        "queue_number": row["queue_number"],
        "reservation_date": row["reservation_date"].isoformat() if row["reservation_date"] else None,
        "expiry_date": row["expiry_date"].isoformat() if row["expiry_date"] else None,
        "status": row["status"],
    }


def _available_items_for_book(cur, book_id: int, library_id: Optional[int]) -> int:
    params: List[Any] = [book_id]
    library_sql = ""
    if library_id is not None:
        library_sql = " AND i.library_id = %s"
        params.append(library_id)

    cur.execute(
        f"""
        SELECT
            COUNT(*) FILTER (
                WHERE NOT EXISTS (
                    SELECT 1 FROM Loan l
                    WHERE l.item_id = i.item_id
                      AND l.return_date IS NULL
                )
            ) AS available_items
        FROM Item i
        WHERE i.book_id = %s
        {library_sql}
        """,
        tuple(params),
    )
    row = cur.fetchone()
    return int(row["available_items"] or 0)


def _first_waiting_reservation(cur, book_id: int) -> Optional[Dict[str, Any]]:
    cur.execute(
        """
        SELECT reservation_id, user_id, status
        FROM Reservation
        WHERE book_id = %s
          AND status IN ('pending', 'ready')
        ORDER BY queue_number ASC
        LIMIT 1
        """,
        (book_id,),
    )
    return cur.fetchone()


@reservation_bp.post("/reservations")
@login_required
def create_reservation() -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}

    if "book_id" not in data:
        return error_response("missing_fields", "Missing required field: book_id.", status=400)

    try:
        book_id = parse_int(
            data["book_id"],
            field="book_id",
            error_code="invalid_ids",
            message="book_id must be an integer.",
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    current = get_current_user()
    user_id = current["user_id"]

    now = datetime.now(timezone.utc)

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "SELECT user_id FROM App_User WHERE user_id = %s AND is_active = TRUE",
                (user_id,),
            )
            if cur.fetchone() is None:
                return error_response("user_not_found", "User not found or inactive.", status=404)

            cur.execute("SELECT book_id FROM Book WHERE book_id = %s", (book_id,))
            if cur.fetchone() is None:
                return error_response("book_not_found", "Book not found.", status=404)

            cur.execute(
                """
                SELECT reservation_id
                FROM Reservation
                WHERE book_id = %s
                  AND user_id = %s
                  AND status IN ('pending', 'ready')
                """,
                (book_id, user_id),
            )
            if cur.fetchone() is not None:
                return error_response(
                    "reservation_exists",
                    "A reservation for this book already exists for the user.",
                    status=409,
                )

            cur.execute(
                "SELECT reservation_id FROM Reservation WHERE book_id = %s FOR UPDATE",
                (book_id,),
            )

            cur.execute(
                """
                SELECT COALESCE(MAX(queue_number), 0) + 1 AS next_pos
                FROM Reservation
                WHERE book_id = %s
                """,
                (book_id,),
            )
            next_pos = int(cur.fetchone()["next_pos"])

            expiry_date = (now + timedelta(days=RESERVATION_EXPIRY_DAYS)).date()

            try:
                cur.execute(
                    """
                    INSERT INTO Reservation (
                        book_id,
                        user_id,
                        queue_number,
                        reservation_date,
                        expiry_date,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING reservation_id, reservation_date, expiry_date, status
                    """,
                    (book_id, user_id, next_pos, now, expiry_date),
                )
            except UniqueViolation:
                return error_response(
                    "reservation_exists",
                    "Reservation already exists or queue conflict occurred. Please retry.",
                    status=409,
                )

            res = cur.fetchone()

            return (
                jsonify(
                    {
                        "reservation_id": res["reservation_id"],
                        "book_id": book_id,
                        "user_id": user_id,
                        "queue_number": next_pos,
                        "reservation_date": res["reservation_date"].isoformat(),
                        "expiry_date": res["expiry_date"].isoformat() if res["expiry_date"] else None,
                        "status": res["status"],
                    }
                ),
                201,
            )

    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)


@reservation_bp.get("/users/<int:user_id>/reservations")
@login_required
def list_reservations_for_user(user_id: int) -> Tuple[Response, int]:
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()
    user_library_id = current.get("library_id")

    if current_role != "admin" and user_id != current_user_id:
        return error_response("forbidden", "You can only list your own reservations.", status=403)

    status = (request.args.get("status") or "all").lower()
    if status != "all" and status not in VALID_STATUSES:
        return error_response("invalid_status", "Invalid status provided.", status=400)

    where = "r.user_id = %s"
    params: List[Any] = [user_id]
    if status != "all":
        where += " AND r.status = %s"
        params.append(status)

    sql = f"""
        SELECT
            r.reservation_id,
            r.book_id,
            r.user_id,
            r.queue_number,
            r.reservation_date,
            r.expiry_date,
            r.status,
            b.title,
            b.author
        FROM Reservation r
        JOIN Book b ON b.book_id = r.book_id
        WHERE {where}
        ORDER BY r.reservation_date DESC
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall() or []

            result = []
            for row in rows:
                cur.execute(
                    """
                    SELECT COUNT(*) AS waiting_ahead
                    FROM Reservation
                    WHERE book_id = %s
                      AND status IN ('pending', 'ready')
                      AND queue_number < %s
                    """,
                    (row["book_id"], row["queue_number"]),
                )
                waiting_ahead = int(cur.fetchone()["waiting_ahead"] or 0)

                first = _first_waiting_reservation(cur, row["book_id"])
                available = _available_items_for_book(cur, row["book_id"], user_library_id)

                can_borrow = (
                    row["status"] in ("pending", "ready")
                    and first is not None
                    and int(first["user_id"]) == int(row["user_id"])
                    and available > 0
                )

                result.append(
                    {
                        "reservation_id": row["reservation_id"],
                        "book_id": row["book_id"],
                        "user_id": row["user_id"],
                        "queue_number": row["queue_number"],
                        "reservation_date": row["reservation_date"].isoformat() if row["reservation_date"] else None,
                        "expiry_date": row["expiry_date"].isoformat() if row["expiry_date"] else None,
                        "status": row["status"],
                        "title": row["title"],
                        "author": row["author"],
                        "waiting_ahead": waiting_ahead,
                        "can_borrow": can_borrow,
                    }
                )

    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return jsonify(result), 200


@reservation_bp.post("/reservations/<int:reservation_id>/cancel")
@login_required
def cancel_reservation(reservation_id: int) -> Tuple[Response, int]:
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT reservation_id, user_id, status
                FROM Reservation
                WHERE reservation_id = %s
                """,
                (reservation_id,),
            )
            row = cur.fetchone()
            if row is None:
                return error_response("reservation_not_found", "Reservation not found.", status=404)

            if current_role != "admin" and int(row["user_id"]) != int(current_user_id):
                return error_response("forbidden", "You can only cancel your own reservations.", status=403)

            if row["status"] in ("fulfilled", "expired"):
                return error_response("invalid_state", "Reservation already closed.", status=400)

            cur.execute(
                """
                UPDATE Reservation
                SET status = 'expired'
                WHERE reservation_id = %s
                RETURNING reservation_id, book_id, user_id, queue_number, reservation_date, expiry_date, status
                """,
                (reservation_id,),
            )
            updated = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return jsonify(_serialize_reservation(updated)), 200


@reservation_bp.post("/reservations/<int:reservation_id>/borrow")
@login_required
def borrow_from_reservation(reservation_id: int) -> Tuple[Response, int]:
    current = get_current_user()
    user_id = current["user_id"]
    user_library_id = current.get("library_id")

    loan_days_raw = (request.get_json(silent=True) or {}).get("loan_days")
    try:
        loan_days = parse_int(
            loan_days_raw if loan_days_raw is not None else DEFAULT_LOAN_DAYS,
            field="loan_days",
            error_code="invalid_loan_days",
            message="loan_days must be an integer.",
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
                SELECT reservation_id, book_id, user_id, status
                FROM Reservation
                WHERE reservation_id = %s
                """,
                (reservation_id,),
            )
            r = cur.fetchone()
            if r is None:
                return error_response("reservation_not_found", "Reservation not found.", status=404)

            if int(r["user_id"]) != int(user_id):
                return error_response("forbidden", "You can only borrow from your own reservation.", status=403)

            if r["status"] not in ("pending", "ready"):
                return error_response("invalid_state", "Reservation is not active.", status=400)

            first = _first_waiting_reservation(cur, r["book_id"])
            if first is None or int(first["reservation_id"]) != int(reservation_id):
                return error_response("not_your_turn", "You are not next in the queue for this book.", status=409)

            params = [r["book_id"]]
            library_filter = ""
            if user_library_id is not None:
                library_filter = " AND i.library_id = %s"
                params.append(user_library_id)

            cur.execute(
                f"""
                SELECT i.item_id
                FROM Item i
                WHERE i.book_id = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM Loan l
                      WHERE l.item_id = i.item_id
                        AND l.return_date IS NULL
                  )
                  {library_filter}
                ORDER BY i.item_id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,
                tuple(params),
            )
            item = cur.fetchone()
            if item is None:
                return error_response("no_available_item", "No available copy right now. Please try again later.", status=409)

            item_id = item["item_id"]

            cur.execute(
                """
                INSERT INTO Loan (item_id, user_id, loan_date, due_date, fine_paid)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING loan_id, loan_date, due_date, fine_paid
                """,
                (item_id, user_id, now, due_date, 0.00),
            )
            loan = cur.fetchone()

            cur.execute(
                """
                UPDATE Reservation
                SET status = 'fulfilled'
                WHERE reservation_id = %s
                """,
                (reservation_id,),
            )

    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return (
        jsonify(
            {
                "status": "ok",
                "reservation_id": reservation_id,
                "loan": {
                    "loan_id": loan["loan_id"],
                    "item_id": item_id,
                    "user_id": user_id,
                    "loan_date": loan["loan_date"].isoformat(),
                    "due_date": loan["due_date"].isoformat(),
                    "fine_paid": float(loan["fine_paid"]) if loan["fine_paid"] is not None else 0.0,
                },
            }
        ),
        200,
    )


@reservation_bp.post("/admin/reservations/expire")
@role_required("admin")
def expire_overdue_reservations() -> Tuple[Response, int]:
    today = date.today()
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE Reservation
                SET status = 'expired'
                WHERE status IN ('pending', 'ready')
                  AND expiry_date IS NOT NULL
                  AND expiry_date < %s
                RETURNING reservation_id
                """,
                (today,),
            )
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return jsonify({"expired_count": len(rows or [])}), 200
