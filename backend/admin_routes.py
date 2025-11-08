from typing import Tuple

from flask import Blueprint, Response, jsonify

from auth_utils import role_required
from db import get_db_cursor
from response_utils import error_response

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin/stats")
@role_required("admin")
def get_stats() -> Tuple[Response, int]:
    """
    GET /api/admin/stats
    Admin-only endpoint.

    Returns high-level system statistics:
      - total_users
      - active_users
      - total_books
      - total_items
      - active_loans
      - overdue_loans
      - total_reservations

    Errors:
      - forbidden (403) if caller is not an admin (handled by @role_required)
      - db_error (500) on database failures
    """
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
