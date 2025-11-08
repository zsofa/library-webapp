from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, jsonify, request
from psycopg2.errors import UniqueViolation

from auth_utils import get_current_user, login_required, role_required
from config import RESERVATION_EXPIRY_DAYS
from db import get_db_cursor
from parse_utils import ParseError, parse_int
from response_utils import error_response

reservation_bp = Blueprint("reservations", __name__)

VALID_STATUSES = {"pending", "ready", "expired", "fulfilled"}


def _serialize_reservation(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a DB row into a JSON-friendly dict for Reservation entities.
    """
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
    """
    Update status with validation and unified error responses.
    Note: This function keeps the original single UPDATE pattern to remain compatible
    with existing tests that mock the DB call sequence (no extra pre-SELECT).
    """
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
    """
    POST /api/reservations

    Errors:
      - missing_fields (400)
      - invalid_ids (400)
      - user_not_found (404)
      - book_not_found (404)
      - reservation_exists (409)
      - db_error (500)
    """
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
            # Ensure user is active
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

            # Ensure book exists
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

            # Check for an existing active reservation (pending or ready)
            # for the same user and book.
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

            # Concurrency-aware queue number assignment with limited retry.
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
                            "A reservation for this book already exists or a queue "
                            "conflict occurred. Please retry.",
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
    """
    GET /api/users/<user_id>/reservations
    Optional query:
      - status=pending|ready|expired|fulfilled|all (default: all)
    """
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
    """
    GET /api/books/<book_id>/reservations
    Admin-only: waiting list ordered by queue_number.
    """
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
    """
    POST /api/reservations/<reservation_id>/status
    Body: { "status": "<pending|ready|expired|fulfilled>" }
    """
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").lower()
    return _change_status(reservation_id, new_status)


@reservation_bp.post("/reservations/<int:reservation_id>/cancel")
@login_required
def cancel_reservation(reservation_id: int) -> Tuple[Response, int]:
    """
    POST /api/reservations/<reservation_id>/cancel
    Users can cancel (expire) their own reservations; Admin may cancel any.
    """
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
    """
    POST /api/admin/reservations/expire
    Admin-only: mark all pending/ready reservations with expiry_date < today as expired.
    Returns: { "expired_count": <int> }
    Errors:
      - forbidden (403) if not admin (handled by decorator)
      - db_error (500)
    """
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
