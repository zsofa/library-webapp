from typing import Optional, Tuple

from flask import Blueprint, Response, jsonify, request

from db import get_db_cursor
from parse_utils import ParseError, parse_int
from response_utils import error_response

book_bp = Blueprint("books", __name__)


@book_bp.get("/books")
def list_books() -> Tuple[Response, int]:
    """
    GET /api/books

    Query:
      - q: case-insensitive substring in title/author
      - category: exact case-insensitive category
      - library_id: optional integer; if provided, totals/availability for that library only
      - page: optional integer, default 1
      - page_size: optional integer, default 20, max 100
    """
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    raw_library_id = (request.args.get("library_id") or "").strip()

    # Pagináció
    page_raw = (request.args.get("page") or "1").strip()
    page_size_raw = (request.args.get("page_size") or "20").strip()

    try:
        page = parse_int(
            page_raw,
            field="page",
            error_code="invalid_pagination",
            message="page must be an integer.",
        )
        page_size = parse_int(
            page_size_raw,
            field="page_size",
            error_code="invalid_pagination",
            message="page_size must be an integer.",
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    if page <= 0 or page_size <= 0 or page_size > 100:
        return error_response(
            "invalid_pagination",
            "page and page_size must be positive, and page_size cannot be greater than 100.",
            status=400,
        )

    offset = (page - 1) * page_size

    # library_id parse
    library_id: Optional[int] = None
    if raw_library_id:
        try:
            library_id = parse_int(
                raw_library_id,
                field="library_id",
                error_code="invalid_library_id",
                message="library_id must be an integer.",
            )
        except ParseError as e:
            return error_response(e.error_code, e.message, status=e.status)

    join_item = """
        LEFT JOIN Item i
            ON i.book_id = b.book_id
    """
    params = []
    if library_id is not None:
        join_item += " AND i.library_id = %s"
        params.append(library_id)

    sql = f"""
        SELECT
            b.book_id,
            b.title,
            b.author,
            b.isbn,
            b.publication_year,
            b.category,
            COUNT(DISTINCT i.item_id) AS total_items,
            COUNT(DISTINCT l.item_id) AS loaned_items
        FROM Book b
        {join_item}
        LEFT JOIN Loan l
            ON l.item_id = i.item_id
           AND l.return_date IS NULL
        WHERE 1=1
    """

    if q:
        sql += " AND (LOWER(b.title) LIKE %s OR LOWER(b.author) LIKE %s)"
        like = f"%{q.lower()}%"
        params.extend([like, like])

    if category:
        sql += " AND LOWER(b.category) = %s"
        params.append(category.lower())

    sql += """
        GROUP BY
            b.book_id,
            b.title,
            b.author,
            b.isbn,
            b.publication_year,
            b.category
        ORDER BY b.title ASC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    result = []
    for row in rows:
        total = row["total_items"] or 0
        loaned = row["loaned_items"] or 0
        available = max(total - loaned, 0)

        result.append(
            {
                "book_id": row["book_id"],
                "title": row["title"],
                "author": row["author"],
                "isbn": row["isbn"],
                "publication_year": row["publication_year"],
                "category": row["category"],
                "total_items": int(total),
                "available_items": int(available),
            }
        )

    return jsonify(result), 200


@book_bp.get("/books/<int:book_id>")
def get_book(book_id: int) -> Tuple[Response, int]:
    """
    GET /api/books/<book_id>
    Return details for a single book including availability.
    Optional library_id query parameter limits counts to a single library.
    """
    raw_library_id = (request.args.get("library_id") or "").strip()

    params = []
    library_filter_sql = ""
    if raw_library_id:
        try:
            library_id = parse_int(
                raw_library_id,
                field="library_id",
                error_code="invalid_library_id",
                message="library_id must be an integer.",
            )
        except ParseError as e:
            return error_response(e.error_code, e.message, status=e.status)
        library_filter_sql = " AND i.library_id = %s"
        params.append(library_id)

    sql = f"""
        SELECT
            b.book_id,
            b.title,
            b.author,
            b.isbn,
            b.publication_year,
            b.category,
            COUNT(DISTINCT i.item_id) AS total_items,
            COUNT(DISTINCT l.item_id) AS loaned_items
        FROM Book b
        LEFT JOIN Item i
            ON i.book_id = b.book_id{library_filter_sql}
        LEFT JOIN Loan l
            ON l.item_id = i.item_id
           AND l.return_date IS NULL
        WHERE b.book_id = %s
        GROUP BY
            b.book_id,
            b.title,
            b.author,
            b.isbn,
            b.publication_year,
            b.category
    """
    params.append(book_id)

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("book_not_found", "Book not found.", status=404)

    total = row["total_items"] or 0
    loaned = row["loaned_items"] or 0
    available = max(total - loaned, 0)

    return (
        jsonify(
            {
                "book_id": row["book_id"],
                "title": row["title"],
                "author": row["author"],
                "isbn": row["isbn"],
                "publication_year": row["publication_year"],
                "category": row["category"],
                "total_items": int(total),
                "available_items": int(available),
            }
        ),
        200,
    )
