from typing import Tuple

from flask import Blueprint, Response, jsonify, request

from auth_utils import get_current_user, login_required
from db import get_db_cursor
from parse_utils import ParseError, parse_date
from response_utils import error_response

user_bp = Blueprint("users", __name__)


@user_bp.get("/users/<int:user_id>")
@login_required
def get_user(user_id: int) -> Tuple[Response, int]:
    """
    GET /api/users/<user_id>
    Return basic profile data for a user.

    Authorization:
      - Non-admin users may only view their own profile (user_id must match the token).
      - Admins may view any user's profile.
    """
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    if current_role != "admin" and user_id != current_user_id:
        return error_response("forbidden", "You can only view your own profile.", status=403)

    sql = """
        SELECT
            u.user_id,
            u.email,
            u.name,
            u.address,
            u.date_of_birth,
            u.library_id,
            r.role_name
        FROM App_User u
        JOIN User_Role r ON u.role_id = r.role_id
        WHERE u.user_id = %s AND u.is_active = TRUE
    """
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("user_not_found", "User not found or not active.", status=404)

    return (
        jsonify(
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "name": row["name"],
                "address": row["address"],
                "date_of_birth": row["date_of_birth"].isoformat() if row["date_of_birth"] else None,
                "library_id": row["library_id"],
                "role": row["role_name"],
            }
        ),
        200,
    )


@user_bp.put("/users/<int:user_id>")
@login_required
def update_user(user_id: int) -> Tuple[Response, int]:
    """
    PUT /api/users/<user_id>
    Update basic profile data (name, address, date_of_birth). Partial updates are allowed.

    Authorization:
      - Non-admin users may only update their own profile (user_id must match the token).
      - Admins may update any user's profile.
    """
    current = get_current_user()
    current_user_id = current["user_id"]
    current_role = (current.get("role") or "").lower()

    if current_role != "admin" and user_id != current_user_id:
        return error_response("forbidden", "You can only update your own profile.", status=403)

    data = request.get_json(silent=True) or {}

    fields = {}

    name = data.get("name")
    if isinstance(name, str) and name.strip():
        fields["name"] = name.strip()

    address = data.get("address")
    if isinstance(address, str) and address.strip():
        fields["address"] = address.strip()

    dob_str = data.get("date_of_birth")
    if dob_str is not None:
        try:
            dob = parse_date(
                dob_str,
                field="date_of_birth",
                error_code="invalid_date_of_birth",
                message="date_of_birth must be in YYYY-MM-DD format.",
            )
        except ParseError as e:
            return error_response(e.error_code, e.message, status=e.status)
        fields["date_of_birth"] = dob

    if not fields:
        return error_response("no_fields_to_update", "No updatable fields provided.", status=400)

    set_clauses = []
    params = []
    for col, value in fields.items():
        set_clauses.append(f"{col} = %s")
        params.append(value)
    params.append(user_id)

    sql = f"""
        UPDATE App_User AS u
        SET {", ".join(set_clauses)}
        FROM User_Role AS r
        WHERE u.user_id = %s
          AND u.is_active = TRUE
          AND u.role_id = r.role_id
        RETURNING
            u.user_id,
            u.email,
            u.name,
            u.address,
            u.date_of_birth,
            u.library_id,
            r.role_name
    """

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("user_not_found", "User not found or not active.", status=404)

    return (
        jsonify(
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "name": row["name"],
                "address": row["address"],
                "date_of_birth": row["date_of_birth"].isoformat() if row["date_of_birth"] else None,
                "library_id": row["library_id"],
                "role": row["role_name"],
            }
        ),
        200,
    )
