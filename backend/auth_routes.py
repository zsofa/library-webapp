from typing import Tuple

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from psycopg2.errors import UniqueViolation

from auth_utils import (  # brute-force protection helpers
    clear_login_attempts,
    get_current_user,
    is_login_blocked,
    login_required,
    register_failed_login,
)
from config import DEFAULT_LIBRARY_ID, DEFAULT_MEMBER_ROLE_ID
from db import get_db_cursor
from parse_utils import ParseError, parse_date, require_fields
from password_policy import is_strong_password  # NEW import
from password_utils import hash_password, verify_password
from response_utils import error_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register() -> Tuple[Response, int]:
    """
    POST /api/register
    Create a new user with default library and member role.
    Errors:
      - missing_fields (400)
      - invalid_date_of_birth (400)
      - weak_password (400)
      - email_exists (409)
      - db_error (500)
    """
    data = request.get_json(silent=True) or {}

    try:
        require_fields(data, ["email", "password", "name", "address", "date_of_birth"])
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    email = data["email"].strip().lower()
    password = data["password"]
    name = data["name"].strip()
    address = data["address"].strip()

    try:
        dob = parse_date(
            data["date_of_birth"],
            field="date_of_birth",
            error_code="invalid_date_of_birth",
            message="date_of_birth must be in YYYY-MM-DD format.",
        )
    except ParseError as e:
        return error_response(e.error_code, e.message, status=e.status)

    # Password strength check before hashing
    ok, reasons = is_strong_password(password)
    if not ok:
        return error_response(
            "weak_password",
            "Password too weak. Rules: min 8 chars, must include a letter and a digit.",
            status=400,
            meta={
                "rules": ["min_length_8", "must_include_letter", "must_include_digit"],
                "violations": reasons,
            },
        )

    password_hash = hash_password(password)

    try:
        with get_db_cursor(commit=True) as cur:
            # Email existence check
            cur.execute(
                """
                SELECT user_id
                FROM App_User
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email,),
            )
            row = cur.fetchone()
            if row is not None:
                return error_response(
                    "email_exists",
                    "A user with this email already exists.",
                    status=409,
                )

            cur.execute(
                """
                INSERT INTO App_User (
                    library_id, role_id, name, address,
                    date_of_birth, email, password_hash, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                RETURNING user_id
                """,
                (
                    DEFAULT_LIBRARY_ID,
                    DEFAULT_MEMBER_ROLE_ID,
                    name,
                    address,
                    dob,
                    email,
                    password_hash,
                ),
            )
            new_id = cur.fetchone()["user_id"]
    except UniqueViolation:
        return error_response(
            "email_exists",
            "A user with this email already exists.",
            status=409,
        )
    except Exception:
        return error_response(
            "db_error",
            "Database error occurred during registration.",
            status=500,
        )

    return (
        jsonify(
            {
                "user_id": new_id,
                "email": email,
                "name": name,
            }
        ),
        201,
    )


@auth_bp.post("/login")
def login() -> Tuple[Response, int]:
    """
    POST /api/login
    Returns: access_token, refresh_token and basic user data.
    Rate-limited per (IP, email).
    Errors:
      - missing_credentials (400)
      - too_many_attempts (429)
      - invalid_credentials (401)
      - db_error (500)
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return error_response(
            "missing_credentials",
            "Email and password are required.",
            status=400,
        )

    blocked, retry_after, remaining = is_login_blocked(email)
    if blocked:
        return error_response(
            "too_many_attempts",
            "Too many login attempts. Try again later.",
            status=429,
            meta={"retry_after": retry_after},
        )

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT
                    u.user_id,
                    u.name,
                    u.email,
                    u.password_hash,
                    u.library_id,
                    r.role_name
                FROM App_User u
                JOIN User_Role r ON u.role_id = r.role_id
                WHERE LOWER(u.email) = LOWER(%s)
                  AND u.is_active = TRUE
                """,
                (email,),
            )
            row = cur.fetchone()
    except Exception:
        return error_response(
            "db_error",
            "Database error occurred during login.",
            status=500,
        )

    if row is None or not verify_password(password, row["password_hash"]):
        register_failed_login(email)
        return error_response(
            "invalid_credentials",
            "Invalid email or password.",
            status=401,
            meta={"remaining_attempts": max((remaining or 0) - 1, 0)},
        )

    # Clear rate limit counter on success
    clear_login_attempts(email)

    # Silent rehash: if legacy MD5 hash detected, upgrade to PBKDF2
    stored = row["password_hash"] or ""
    if len(stored) == 32 and ":" not in stored:
        try:
            new_hash = hash_password(password)
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE App_User SET password_hash = %s WHERE user_id = %s",
                    (new_hash, row["user_id"]),
                )
        except Exception:
            # Non-critical: ignore silent rehash failure
            pass

    access_token = create_access_token(
        identity=str(row["user_id"]),
        additional_claims={
            "role": row["role_name"],
            "library_id": row["library_id"],
        },
    )
    refresh_token = create_refresh_token(
        identity=str(row["user_id"]),
        additional_claims={
            "role": row["role_name"],
            "library_id": row["library_id"],
        },
    )

    user_data = {
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role_name"],
        "library_id": row["library_id"],
    }

    return (
        jsonify({"access_token": access_token, "refresh_token": refresh_token, "user": user_data}),
        200,
    )


@auth_bp.post("/token/refresh")
@jwt_required(refresh=True)
def refresh_access_token() -> Tuple[Response, int]:
    """
    POST /api/token/refresh
    Requires a valid refresh token. Returns a new access token preserving claims.
    """
    raw_id = get_jwt_identity()
    claims = get_jwt() or {}
    new_access = create_access_token(
        identity=str(raw_id),
        additional_claims={
            "role": claims.get("role"),
            "library_id": claims.get("library_id"),
        },
    )
    return jsonify({"access_token": new_access}), 200


@auth_bp.post("/logout")
@login_required
def logout() -> Tuple[Response, int]:
    """
    POST /api/logout
    Revokes the current access token by adding its JTI to the in-memory blocklist.
    """
    jti = (get_jwt() or {}).get("jti")
    if not jti:
        return error_response("unauthorized", "Missing or invalid token.", status=401)

    blocklist = current_app.config.get("JWT_BLOCKLIST")
    if isinstance(blocklist, set):
        blocklist.add(jti)

    return jsonify({"status": "ok"}), 200


@auth_bp.get("/me")
@login_required
def me() -> Tuple[Response, int]:
    """
    GET /api/me
    Return current user information extracted from the JWT claims.
    """
    user = get_current_user()
    return (
        jsonify(
            {
                "user_id": user["user_id"],
                "role": user["role"],
                "library_id": user["library_id"],
            }
        ),
        200,
    )


@auth_bp.post("/me/password")
@login_required
def change_password() -> Tuple[Response, int]:
    """
    POST /api/me/password
    Body: { "old_password": "...", "new_password": "..." }
    Errors:
      - missing_fields (400)
      - invalid_credentials (401) (old password wrong)
      - weak_password (400)
      - user_not_found (404)
      - db_error (500)
    """
    data = request.get_json(silent=True) or {}
    old_pw = data.get("old_password") or ""
    new_pw = data.get("new_password") or ""

    if not old_pw or not new_pw:
        return error_response(
            "missing_fields", "old_password and new_password are required.", status=400
        )

    user = get_current_user()
    user_id = user["user_id"]

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT password_hash FROM App_User WHERE user_id = %s AND is_active = TRUE",
                (user_id,),
            )
            row = cur.fetchone()
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    if row is None:
        return error_response("user_not_found", "User not found or inactive.", status=404)

    if not verify_password(old_pw, row.get("password_hash") or ""):
        return error_response("invalid_credentials", "Old password is incorrect.", status=401)

    ok, reasons = is_strong_password(new_pw)
    if not ok:
        return error_response(
            "weak_password",
            "New password too weak. Rules: min 8 chars, must include a letter and a digit.",
            status=400,
            meta={"violations": reasons},
        )

    try:
        new_hash = hash_password(new_pw)
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE App_User SET password_hash = %s WHERE user_id = %s",
                (new_hash, user_id),
            )
    except Exception:
        return error_response("db_error", "Database error occurred.", status=500)

    return jsonify({"status": "ok"}), 200
