import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

from flask import current_app, g, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from response_utils import forbidden, unauthorized


def _ensure_jwt_verified() -> bool:
    """
    Internal helper to avoid running verify_jwt_in_request() multiple times
    if both @login_required and @role_required wrap the same endpoint.
    """
    if getattr(g, "_jwt_verified", False):
        return True
    try:
        verify_jwt_in_request()
        g._jwt_verified = True
        return True
    except Exception:
        return False


def login_required(fn: Callable) -> Callable:
    """
    Require a valid JWT for accessing the endpoint.
    Unified 401 error JSON if missing / invalid.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        if not _ensure_jwt_verified():
            return unauthorized()
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles: str) -> Callable:
    """
    Require at least one of the given roles (case-insensitive).
    Example:
      @role_required("admin")
      @role_required("Admin", "Supervisor")

    Returns 401 if token invalid, 403 if role not in allowed set.
    """
    allowed = {r.lower() for r in roles}

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            if not _ensure_jwt_verified():
                return unauthorized()

            claims = get_jwt()
            role = (claims.get("role") or "").lower()
            if role not in allowed:
                return forbidden("Insufficient permissions.")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user() -> Dict[str, Any]:
    """
    Return current user info from the JWT (user_id, role, library_id).

    Assumes verify_jwt_in_request() has already occurred via wrapper.
    Caches result in flask.g for multiple calls within the same request.
    """
    cached = getattr(g, "_current_user_claims", None)
    if cached:
        return cached

    claims = get_jwt()
    raw_id = get_jwt_identity()
    try:
        user_id = int(raw_id)
    except (TypeError, ValueError):
        user_id = raw_id

    result = {
        "user_id": user_id,
        "role": claims.get("role"),
        "library_id": claims.get("library_id"),
    }
    g._current_user_claims = result
    return result


# -----------------------------
# Basic brute-force protection for /login
# -----------------------------
#
# - Tracks failed login attempts per (IP, email) pair.
# - Uses a simple in-memory (process local) deque of timestamps.
# - If LOGIN_RATE_LIMIT_ATTEMPTS is exceeded within LOGIN_RATE_LIMIT_WINDOW_S,
#   subsequent attempts from the same IP+email are temporarily blocked.
# - Counters reset automatically after window expires or a successful login.
#
# NOTE:
#   - This is intentionally lightweight. In a production multi-worker setup,
#     this should live in Redis or another shared store to be globally effective.


# (ip, email) -> deque[timestamps]
_login_attempts: Dict[Tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=128))


def _rate_key(email: str) -> Tuple[str, str]:
    ip = request.remote_addr or "unknown"
    return ip, (email or "").lower().strip()


def is_login_blocked(email: str) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Returns:
      (blocked: bool, retry_after_seconds: int|None, remaining_attempts: int|None)

    - Does NOT record a failed attempt. It only checks the current window.
    - retry_after_seconds is the number of seconds until attempts are allowed again.
    - remaining_attempts is how many failed attempts are left before blocking.
    """
    k = _rate_key(email)
    dq = _login_attempts[k]
    now = time.time()
    # read config from Flask app config (must be set in config.py)
    window = current_app.config.get("LOGIN_RATE_LIMIT_WINDOW_S", 900)
    max_attempts = current_app.config.get("LOGIN_RATE_LIMIT_ATTEMPTS", 5)

    # Drop outdated timestamps
    while dq and now - dq[0] > window:
        dq.popleft()

    if len(dq) >= max_attempts:
        retry_after = int(window - (now - dq[0]))
        return True, max(retry_after, 0), 0

    remaining = max_attempts - len(dq)
    return False, None, remaining


def register_failed_login(email: str) -> None:
    """Record a failed login attempt timestamp for the (IP, email) key."""
    k = _rate_key(email)
    _login_attempts[k].append(time.time())


def clear_login_attempts(email: str) -> None:
    """Clear the counter for this (IP, email) key after a successful login."""
    k = _rate_key(email)
    dq = _login_attempts.get(k)
    if dq:
        dq.clear()
