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
        "reservation_date": (
            row["reservation_date"].isoformat() if row["reservation_date"] else None
        ),
        "expiry_date": row["expiry_date"].isoformat() if row["expiry_date"] else None,
        "status": row["status"],
    }


def _change_status(reservation_id: int, new_status: str) -> Tuple[Response, int]:
    if new_status not in VALID_STATUSES:
        return error_response(
            "invalid_status",
            "Invalid status provided. Valid statuses are: pending, ready, expired, fulfilled.",
            status=400,
        )

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE Reservation
                SET status = %s
                WHERE reservation_id = %s
                RETURNING reservation_id,
                          book_id,
                          user_id,
                          queue_number,
                          reservation_date,
                          expiry_date,
                          status
                """,
                (new_status, reservation_id),
            )
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("reservation_not_found", "Reservation not found.", status=404)

    return jsonify(_serialize_reservation(row)), 200


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
                """
                SELECT user_id
                FROM App_User
                WHERE user_id = %s AND is_active = TRUE
                """,
                (user_id,),
            )
            user = cur.fetchone()
            if user is None:
                return error_response("user_not_found", "User not found or inactive.", status=404)

            cur.execute(
                """
                SELECT book_id
                FROM Book
                WHERE book_id = %s
                """,
                (book_id,),
            )
            book = cur.fetchone()
            if book is None:
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
            existing = cur.fetchone()
            if existing is not None:
                return error_response(
                    "reservation_exists",
                    "A reservation for this book already exists for the user.",
                    status=409,
                )

            attempts = 0
            max_attempts = 3
            res = None
            next_pos: Optional[int] = None

            while attempts < max_attempts:
                attempts += 1

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
                next_pos = cur.fetchone()["next_pos"]

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
                    res = cur.fetchone()
                    break
                except UniqueViolation:
                    if attempts >= max_attempts:
                        return error_response(
                            "reservation_exists",
                            "A reservation for this book already exists or a queue conflict occurred. Please retry.",
                            status=409,
                        )
                    # retry

            return (
                jsonify(
                    {
                        "reservation_id": res["reservation_id"],
                        "book_id": book_id,
                        "user_id": user_id,
                        "queue_number": next_pos,
                        "reservation_date": res["reservation_date"].isoformat(),
                        "expiry_date": (
                            res["expiry_date"].isoformat() if res["expiry_date"] else None
                        ),
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

    if current_role != "admin" and user_id != current_user_id:
        return error_response("forbidden", "You can only list your own reservations.", status=403)

    status = (request.args.get("status") or "all").lower()

    where = "user_id = %s"
    params: List[Any] = [user_id]

    if status != "all":
        if status not in VALID_STATUSES:
            return error_response(
                "invalid_status",
                "Invalid status provided. Valid statuses are: pending, ready, expired, fulfilled.",
                status=400,
            )
        where += " AND status = %s"
        params.append(status)

    sql = f"""
        SELECT
            reservation_id,
            book_id,
            user_id,
            queue_number,
            reservation_date,
            expiry_date,
            status
        FROM Reservation
        WHERE {where}
        ORDER BY reservation_date DESC
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return jsonify([_serialize_reservation(r) for r in rows]), 200


@reservation_bp.get("/books/<int:book_id>/reservations")
@role_required("admin")
def list_reservations_for_book(book_id: int) -> Tuple[Response, int]:
    sql = """
        SELECT
            reservation_id,
            book_id,
            user_id,
            queue_number,
            reservation_date,
            expiry_date,
            status
        FROM Reservation
        WHERE book_id = %s
        ORDER BY queue_number ASC
    """
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, (book_id,))
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return jsonify([_serialize_reservation(r) for r in rows]), 200


@reservation_bp.post("/reservations/<int:reservation_id>/status")
@role_required("admin")
def update_reservation_status(reservation_id: int) -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").lower()
    return _change_status(reservation_id, new_status)


@reservation_bp.post("/reservations/<int:reservation_id>/cancel")
@login_required
def cancel_reservation(reservation_id: int) -> Tuple[Response, int]:
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT reservation_id, user_id
                FROM Reservation
                WHERE reservation_id = %s
                """,
                (reservation_id,),
            )
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("reservation_not_found", "Reservation not found.", status=404)

    if current_role != "admin" and row["user_id"] != current_user_id:
        return error_response("forbidden", "You can only cancel your own reservations.", status=403)

    return _change_status(reservation_id, "expired")


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


@reservation_bp.post("/admin/books/<int:book_id>/issue")
@role_required("admin")
def issue_book_to_next_reservation(book_id: int) -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    loan_days_raw = data.get("loan_days", DEFAULT_LOAN_DAYS)

    try:
        loan_days = parse_int(
            loan_days_raw,
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
            cur.execute("SELECT book_id FROM Book WHERE book_id = %s", (book_id,))
            if cur.fetchone() is None:
                return error_response("book_not_found", "Book not found.", status=404)

            cur.execute(
                """
                SELECT reservation_id, user_id, queue_number, status
                FROM Reservation
                WHERE book_id = %s
                  AND status IN ('pending', 'ready')
                ORDER BY queue_number ASC
                FOR UPDATE
                LIMIT 1
                """,
                (book_id,),
            )
            res = cur.fetchone()
            if res is None:
                return error_response(
                    "no_reservation",
                    "No pending/ready reservation for this book.",
                    status=409,
                )

            reservation_id = res["reservation_id"]
            target_user_id = res["user_id"]

            cur.execute(
                """
                SELECT i.item_id
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
                """,
                (book_id,),
            )
            item = cur.fetchone()
            if item is None:
                return error_response("no_available_item", "No available copy to loan.", status=409)

            item_id = item["item_id"]

            cur.execute(
                """
                INSERT INTO Loan (item_id, user_id, loan_date, due_date, fine_paid)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING loan_id, loan_date, due_date
                """,
                (item_id, target_user_id, now, due_date, 0.00),
            )
            loan = cur.fetchone()

            cur.execute(
                """
                UPDATE Reservation
                SET status = 'fulfilled'
                WHERE reservation_id = %s
                RETURNING reservation_id, status
                """,
                (reservation_id,),
            )
            _ = cur.fetchone()

    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return (
        jsonify(
            {
                "status": "ok",
                "book_id": book_id,
                "reservation_id": reservation_id,
                "user_id": target_user_id,
                "item_id": item_id,
                "loan": {
                    "loan_id": loan["loan_id"],
                    "loan_date": loan["loan_date"].isoformat() if loan["loan_date"] else None,
                    "due_date": loan["due_date"].isoformat() if loan["due_date"] else None,
                },
            }
        ),
        200,
    )
