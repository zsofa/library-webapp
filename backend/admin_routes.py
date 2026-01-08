from datetime import datetime, timezone
from typing import Tuple, Optional, List, Any

from flask import Blueprint, Response, jsonify, request

from auth_utils import role_required
from config import DEFAULT_LIBRARY_ID
from db import get_db_cursor
from parse_utils import ParseError, parse_int
from response_utils import error_response

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin/books/<int:book_id>/items")
@role_required("admin")
def list_items_for_book(book_id: int) -> Tuple[Response, int]:
    available_only = (request.args.get("available_only") or "false").lower() == "true"

    where_extra = ""
    if available_only:
        where_extra = """
          AND NOT EXISTS (
            SELECT 1 FROM Loan l
            WHERE l.item_id = i.item_id
              AND l.return_date IS NULL
          )
        """

    sql = f"""
      SELECT
        i.item_id,
        i.book_id,
        i.library_id,
        i.item_condition,
        i.shelf_mark,
        EXISTS (
          SELECT 1 FROM Loan l
          WHERE l.item_id = i.item_id
            AND l.return_date IS NULL
        ) AS is_loaned
      FROM Item i
      WHERE i.book_id = %s
      {where_extra}
      ORDER BY i.item_id ASC
    """

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT book_id FROM Book WHERE book_id = %s", (book_id,))
            if cur.fetchone() is None:
                return error_response("book_not_found", "Book not found.", status=404)

            cur.execute(sql, (book_id,))
            rows = cur.fetchall() or []
    except Exception as e:
        return error_response("db_error", str(e), status=500)

    return jsonify(rows), 200


@admin_bp.post("/admin/books/<int:book_id>/items")
@role_required("admin")
def add_items_for_book(book_id: int) -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    count_raw = data.get("count", 1)
    library_id_raw = data.get("library_id")
    item_condition = (data.get("item_condition") or "new").strip().lower()
    shelf_mark_prefix = (data.get("shelf_mark_prefix") or "AUTO").strip()

    allowed_conditions = {"new", "good", "used", "damaged"}
    if item_condition not in allowed_conditions:
        return error_response(
            "invalid_item_condition",
            "item_condition must be one of: new, good, used, damaged.",
            status=400,
        )

    try:
        count = parse_int(count_raw, field="count", error_code="invalid_count", message="count must be an integer.")
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    if count <= 0 or count > 200:
        return error_response("invalid_count", "count must be between 1 and 200.", status=400)

    library_id: int = DEFAULT_LIBRARY_ID
    if library_id_raw is not None and str(library_id_raw).strip() != "":
        try:
            library_id = parse_int(
                library_id_raw,
                field="library_id",
                error_code="invalid_library_id",
                message="library_id must be an integer.",
            )
        except ParseError as e:
            return error_response(e.error_code, e.message, status=e.status)

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT book_id FROM Book WHERE book_id = %s", (book_id,))
            if cur.fetchone() is None:
                return error_response("book_not_found", "Book not found.", status=404)

            cur.execute("SELECT library_id FROM Library WHERE library_id = %s", (library_id,))
            if cur.fetchone() is None:
                return error_response("library_not_found", "Library not found.", status=400)

            inserted_ids: List[int] = []
            now = datetime.now(timezone.utc)
            stamp = int(now.timestamp())

            for idx in range(count):
                shelf_mark = f"{shelf_mark_prefix}-{book_id}-{stamp}-{idx+1}"
                cur.execute(
                    """
                    INSERT INTO Item (book_id, library_id, item_condition, shelf_mark)
                    VALUES (%s, %s, %s, %s)
                    RETURNING item_id
                    """,
                    (book_id, library_id, item_condition, shelf_mark),
                )
                inserted_ids.append(int(cur.fetchone()["item_id"]))

    except Exception as e:
        return error_response("db_error", str(e), status=500)

    return (
        jsonify(
            {
                "status": "ok",
                "book_id": book_id,
                "created_count": len(inserted_ids),
                "item_ids": inserted_ids,
                "item_condition": item_condition,
                "library_id": library_id,
                "shelf_mark_prefix": shelf_mark_prefix,
            }
        ),
        201,
    )


@admin_bp.post("/admin/books/<int:book_id>/items/remove_one")
@role_required("admin")
def remove_one_available_item(book_id: int) -> Tuple[Response, int]:
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT book_id FROM Book WHERE book_id = %s", (book_id,))
            if cur.fetchone() is None:
                return error_response("book_not_found", "Book not found.", status=404)

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
                return error_response("no_removable_item", "No removable (available) copy for this book.", status=409)

            item_id = int(item["item_id"])
            cur.execute("DELETE FROM Item WHERE item_id = %s", (item_id,))

    except Exception as e:
        return error_response("db_error", str(e), status=500)

    return jsonify({"status": "ok", "book_id": book_id, "removed_item_id": item_id}), 200
