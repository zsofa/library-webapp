from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

from flask import Blueprint, Response, jsonify, request
from psycopg2.errors import UniqueViolation

from auth_utils import get_current_user, login_required, role_required
from config import DEFAULT_LOAN_DAYS
from db import get_db_cursor
from parse_utils import ParseError, parse_int
from response_utils import error_response

loan_bp = Blueprint("loans", __name__)


def _pick_available_item(cur, book_id: int, user_library_id: Optional[int]) -> Optional[dict]:
    params = [book_id]
    library_filter = ""
    if user_library_id is not None:
        library_filter = " AND i.library_id = %s"
        params.append(user_library_id)

    sql = f"""
        SELECT i.item_id, i.book_id, i.library_id
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
    """
    cur.execute(sql, tuple(params))
    return cur.fetchone()


@loan_bp.post("/loans")
@login_required
def create_loan() -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}

    item_id = data.get("item_id")
    book_id = data.get("book_id")
    raw_loan_days = data.get("loan_days")

    if not item_id and not book_id:
        return error_response(
            "missing_fields",
            "Either item_id or book_id must be provided.",
            status=400,
        )

    try:
        loan_days = (
            parse_int(
                raw_loan_days,
                field="loan_days",
                error_code="invalid_loan_days",
                message="loan_days must be an integer.",
            )
            if raw_loan_days is not None
            else DEFAULT_LOAN_DAYS
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    if loan_days <= 0:
        return error_response(
            "invalid_loan_days", "loan_days must be a positive integer.", status=400
        )

    current = get_current_user()
    user_id = current["user_id"]
    user_library_id = current.get("library_id")

    now = datetime.now(timezone.utc)
    due_date = (now + timedelta(days=loan_days)).date()

    try:
        with get_db_cursor(commit=True) as cur:
            chosen_item = None

            if item_id is not None:
                try:
                    item_id = parse_int(
                        item_id,
                        field="item_id",
                        error_code="invalid_ids",
                        message="item_id must be an integer.",
                    )
                except ParseError as e:
                    return error_response(e.error_code, e.message, status=e.status)

                cur.execute(
                    """
                    SELECT item_id, book_id, library_id
                    FROM Item
                    WHERE item_id = %s
                    """,
                    (item_id,),
                )
                chosen_item = cur.fetchone()
                if chosen_item is None:
                    return error_response("item_not_found", "Item not found.", status=404)

                if user_library_id is not None and user_library_id != chosen_item["library_id"]:
                    return error_response(
                        "different_library",
                        "User and item are from different libraries.",
                        status=400,
                    )

                cur.execute(
                    """
                    SELECT loan_id
                    FROM Loan
                    WHERE item_id = %s AND return_date IS NULL
                    """,
                    (item_id,),
                )
                active = cur.fetchone()
                if active is not None:
                    return error_response(
                        "item_already_loaned", "This item is already loaned out.", status=409
                    )

            else:
                try:
                    book_id = parse_int(
                        book_id,
                        field="book_id",
                        error_code="invalid_ids",
                        message="book_id must be an integer.",
                    )
                except ParseError as e:
                    return error_response(e.error_code, e.message, status=e.status)

                cur.execute(
                    """
                    SELECT book_id
                    FROM Book
                    WHERE book_id = %s
                    """,
                    (book_id,),
                )
                book_row = cur.fetchone()
                if book_row is None:
                    return error_response("book_not_found", "Book not found.", status=404)

                chosen_item = _pick_available_item(cur, book_id, user_library_id)
                if chosen_item is None:
                    return error_response(
                        "no_available_item", "No available item for this book.", status=409
                    )
                item_id = chosen_item["item_id"]

            cur.execute(
                """
                INSERT INTO Loan (item_id, user_id, loan_date, due_date, fine_paid)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING loan_id, loan_date, due_date, fine_paid
                """,
                (item_id, user_id, now, due_date, 0.00),
            )
            loan = cur.fetchone()
    except UniqueViolation:
        return error_response("item_already_loaned", "This item is already loaned out.", status=409)
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return (
        jsonify(
            {
                "loan_id": loan["loan_id"],
                "item_id": item_id,
                "book_id": chosen_item["book_id"] if chosen_item else None,
                "user_id": user_id,
                "loan_date": loan["loan_date"].isoformat(),
                "due_date": loan["due_date"].isoformat(),
                "fine_paid": float(loan["fine_paid"]) if loan["fine_paid"] is not None else 0.0,
                "status": "active",
            }
        ),
        201,
    )


@loan_bp.post("/loans/<int:loan_id>/return")
@login_required
def return_loan(loan_id: int) -> Tuple[Response, int]:
    now = datetime.now(timezone.utc)
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT loan_id, item_id, user_id, loan_date, due_date, return_date, fine_paid
                FROM Loan
                WHERE loan_id = %s
                """,
                (loan_id,),
            )
            row = cur.fetchone()

            if row is None:
                return error_response("loan_not_found", "Loan not found.", status=404)

            if current_role != "admin" and row["user_id"] != current_user_id:
                return error_response(
                    "forbidden", "You can only return your own loans.", status=403
                )

            if row["return_date"] is not None:
                return error_response("loan_already_returned", "Loan already returned.", status=400)

            cur.execute(
                """
                UPDATE Loan
                SET return_date = %s
                WHERE loan_id = %s
                RETURNING loan_id, item_id, user_id, loan_date, due_date, return_date, fine_paid
                """,
                (now, loan_id),
            )
            updated = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return (
        jsonify(
            {
                "loan_id": updated["loan_id"],
                "item_id": updated["item_id"],
                "user_id": updated["user_id"],
                "loan_date": updated["loan_date"].isoformat() if updated["loan_date"] else None,
                "due_date": updated["due_date"].isoformat() if updated["due_date"] else None,
                "return_date": (
                    updated["return_date"].isoformat() if updated["return_date"] else None
                ),
                "fine_paid": (
                    float(updated["fine_paid"]) if updated["fine_paid"] is not None else 0.0
                ),
            }
        ),
        200,
    )


@loan_bp.post("/loans/<int:loan_id>/extend")
@login_required
def extend_loan(loan_id: int) -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}

    try:
        extra_days = parse_int(
            data.get("extra_days"),
            field="extra_days",
            error_code="invalid_extra_days",
            message="extra_days must be an integer.",
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    if extra_days <= 0:
        return error_response(
            "invalid_extra_days", "extra_days must be a positive integer.", status=400
        )

    today = date.today()
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT loan_id, item_id, user_id, loan_date, due_date, return_date, fine_paid
                FROM Loan
                WHERE loan_id = %s
                """,
                (loan_id,),
            )
            row = cur.fetchone()
            if row is None:
                return error_response("loan_not_found", "Loan not found.", status=404)

            if current_role != "admin" and row["user_id"] != current_user_id:
                return error_response(
                    "forbidden", "You can only extend your own loans.", status=403
                )

            if row["return_date"] is not None:
                return error_response("loan_already_returned", "Loan already returned.", status=400)

            raw_due = row["due_date"]
            due_as_date = raw_due.date() if isinstance(raw_due, datetime) else raw_due

            if due_as_date is not None and due_as_date < today:
                return error_response(
                    "loan_overdue", "Overdue loans cannot be extended.", status=400
                )

            new_due = (due_as_date or today) + timedelta(days=extra_days)
            cur.execute(
                """
                UPDATE Loan
                SET due_date = %s
                WHERE loan_id = %s
                RETURNING loan_id, item_id, user_id, loan_date, due_date, return_date, fine_paid
                """,
                (new_due, loan_id),
            )
            updated = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return (
        jsonify(
            {
                "loan_id": updated["loan_id"],
                "item_id": updated["item_id"],
                "user_id": updated["user_id"],
                "loan_date": updated["loan_date"].isoformat() if updated["loan_date"] else None,
                "due_date": updated["due_date"].isoformat() if updated["due_date"] else None,
                "return_date": (
                    updated["return_date"].isoformat() if updated["return_date"] else None
                ),
                "fine_paid": (
                    float(updated["fine_paid"]) if updated["fine_paid"] is not None else 0.0
                ),
            }
        ),
        200,
    )


@loan_bp.get("/users/<int:user_id>/loans")
@login_required
def list_loans_for_user(user_id: int) -> Tuple[Response, int]:
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    if current_role != "admin" and user_id != current_user_id:
        return error_response("forbidden", "You can only list your own loans.", status=403)

    active_param = (request.args.get("active") or "true").lower()
    overdue_param = (request.args.get("overdue") or "false").lower()

    where = "l.user_id = %s"
    params = [user_id]

    if active_param == "true":
        where += " AND l.return_date IS NULL"
    elif active_param == "false":
        where += " AND l.return_date IS NOT NULL"

    if overdue_param == "true":
        where += " AND l.return_date IS NULL AND l.due_date < CURRENT_DATE"

    sql = f"""
        SELECT
            l.loan_id,
            l.item_id,
            l.user_id,
            l.loan_date,
            l.due_date,
            l.return_date,
            l.fine_paid,
            i.book_id,
            b.title AS book_title,
            b.author AS book_author
        FROM Loan l
        JOIN Item i ON i.item_id = l.item_id
        JOIN Book b ON b.book_id = i.book_id
        WHERE {where}
        ORDER BY l.loan_date DESC
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    def serialize(row):
        return {
            "loan_id": row["loan_id"],
            "item_id": row["item_id"],
            "user_id": row["user_id"],
            "loan_date": row["loan_date"].isoformat() if row["loan_date"] else None,
            "due_date": row["due_date"].isoformat() if row["due_date"] else None,
            "return_date": row["return_date"].isoformat() if row["return_date"] else None,
            "fine_paid": float(row["fine_paid"]) if row["fine_paid"] is not None else 0.0,
            "book_id": row["book_id"],
            "book_title": row["book_title"],
            "book_author": row["book_author"],
        }

    return jsonify([serialize(r) for r in rows]), 200



@loan_bp.get("/loans/overdue")
@role_required("admin")
def list_overdue_loans() -> Tuple[Response, int]:
    sql = """
        SELECT
            loan_id,
            item_id,
            user_id,
            loan_date,
            due_date,
            return_date,
            fine_paid
        FROM Loan
        WHERE return_date IS NULL
          AND due_date < CURRENT_DATE
        ORDER BY due_date ASC
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    def serialize(row):
        return {
            "loan_id": row["loan_id"],
            "item_id": row["item_id"],
            "user_id": row["user_id"],
            "loan_date": row["loan_date"].isoformat() if row["loan_date"] else None,
            "due_date": row["due_date"].isoformat() if row["due_date"] else None,
            "return_date": row["return_date"].isoformat() if row["return_date"] else None,
            "fine_paid": float(row["fine_paid"]) if row["fine_paid"] is not None else 0.0,
        }

    return jsonify([serialize(r) for r in rows]), 200


@loan_bp.get("/me/loans/details")
@login_required
def my_loans_with_book_details() -> Tuple[Response, int]:
    """
    GET /api/me/loans/details?active=true|false|all
    Visszaadja a saját kölcsönzéseket úgy, hogy benne van:
      - book_id, title, author
      - item_id
      - loan_date, due_date, return_date
    """
    current = get_current_user()
    user_id = current["user_id"]

    active_param = (request.args.get("active") or "true").lower()

    where = "l.user_id = %s"
    params = [user_id]

    if active_param == "true":
        where += " AND l.return_date IS NULL"
    elif active_param == "false":
        where += " AND l.return_date IS NOT NULL"

    sql = f"""
        SELECT
            l.loan_id,
            l.item_id,
            l.user_id,
            l.loan_date,
            l.due_date,
            l.return_date,
            l.fine_paid,
            b.book_id,
            b.title,
            b.author
        FROM Loan l
        JOIN Item i ON i.item_id = l.item_id
        JOIN Book b ON b.book_id = i.book_id
        WHERE {where}
        ORDER BY l.loan_date DESC
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    result = []
    for r in rows:
        result.append(
            {
                "loan_id": r["loan_id"],
                "item_id": r["item_id"],
                "user_id": r["user_id"],
                "loan_date": r["loan_date"].isoformat() if r["loan_date"] else None,
                "due_date": r["due_date"].isoformat() if r["due_date"] else None,
                "return_date": r["return_date"].isoformat() if r["return_date"] else None,
                "fine_paid": float(r["fine_paid"]) if r["fine_paid"] is not None else 0.0,
                "book_id": r["book_id"],
                "title": r["title"],
                "author": r["author"],
            }
        )

    return jsonify(result), 200
