import hashlib

from psycopg2.errors import UniqueViolation

import auth_routes
from tests.conftest import make_get_db_cursor

# ----- REGISTER TESTS ----- #


def test_register_missing_fields(client):
    r = client.post("/api/register", json={"email": "x@y.z"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_fields"


def test_register_invalid_dob(client):
    payload = {
        "email": "a@b.c",
        "password": "Strong123",  # valid password form
        "name": "User",
        "address": "Addr",
        "date_of_birth": "01-01-2000",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_date_of_birth"


def test_register_weak_password(client):
    payload = {
        "email": "weak@example.com",
        "password": "pw",  # deliberately weak
        "name": "Weak User",
        "address": "Addr",
        "date_of_birth": "2000-01-01",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "weak_password"
    assert "violations" in body.get("meta", {})


def test_register_duplicate_email(client, monkeypatch):
    # First SELECT returns existing user -> email_exists (409)
    monkeypatch.setattr(
        auth_routes,
        "get_db_cursor",
        make_get_db_cursor(fetchone={"user_id": 1}),
    )
    payload = {
        "email": "dup@example.com",
        "password": "Strong123",
        "name": "User",
        "address": "Addr",
        "date_of_birth": "2000-01-01",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 409
    assert r.get_json()["error"] == "email_exists"


def test_register_unique_violation_race_condition(client, monkeypatch):
    """
    Simulate race: first SELECT finds no user, INSERT raises UniqueViolation.
    Expect email_exists (409).
    """

    class CursorWithUnique:
        def __init__(self):
            self._fetchone_iter = iter([None])  # first SELECT -> None
            self._calls = 0

        def execute(self, sql, params=None):
            self._calls += 1
            # After SELECT (call 1), attempt INSERT (call 2) -> raise UniqueViolation
            if self._calls >= 2:
                raise UniqueViolation()

        def fetchone(self):
            try:
                return next(self._fetchone_iter)
            except StopIteration:
                return None

        def fetchall(self):
            return []

    class CM:
        def __enter__(self):
            return CursorWithUnique()

        def __exit__(self, exc_type, exc, tb):
            return False

    def _get_db_cursor(commit=False):
        return CM()

    monkeypatch.setattr(auth_routes, "get_db_cursor", _get_db_cursor)

    payload = {
        "email": "race@example.com",
        "password": "Strong123",
        "name": "User",
        "address": "Addr",
        "date_of_birth": "2000-01-01",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 409
    assert r.get_json()["error"] == "email_exists"


def test_register_success(client, monkeypatch):
    # Sequence: first SELECT (None), then INSERT returning user_id
    monkeypatch.setattr(
        auth_routes,
        "get_db_cursor",
        make_get_db_cursor(fetchone=[None, {"user_id": 123}]),
    )
    payload = {
        "email": "ok@example.com",
        "password": "Strong123",
        "name": "Ok User",
        "address": "Addr",
        "date_of_birth": "2000-01-01",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 201
    body = r.get_json()
    assert body["user_id"] == 123
    assert body["email"] == "ok@example.com"


def test_register_db_error(client, monkeypatch):
    # DB context manager raises on enter
    monkeypatch.setattr(
        auth_routes,
        "get_db_cursor",
        make_get_db_cursor(raise_on_enter=True),
    )
    payload = {
        "email": "e@example.com",
        "password": "Strong123",
        "name": "User",
        "address": "Addr",
        "date_of_birth": "2000-01-01",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"


# ----- LOGIN TESTS ----- #


def test_login_missing_credentials(client):
    r = client.post("/api/login", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_credentials"


def test_login_nonexistent_email(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "get_db_cursor",
        make_get_db_cursor(fetchone=None),
    )
    r = client.post("/api/login", json={"email": "none@example.com", "password": "x"})
    assert r.status_code == 401
    assert r.get_json()["error"] == "invalid_credentials"


def test_login_wrong_password(client, monkeypatch):
    good_hash = hashlib.md5(b"correct").hexdigest()
    row = {
        "user_id": 1,
        "name": "User",
        "email": "u@e.m",
        "password_hash": good_hash,
        "library_id": 1,
        "role_name": "Member",
    }
    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    r = client.post("/api/login", json={"email": "u@e.m", "password": "wrong"})
    assert r.status_code == 401
    assert r.get_json()["error"] == "invalid_credentials"


def test_login_db_error(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "get_db_cursor",
        make_get_db_cursor(raise_on_enter=True),
    )
    r = client.post("/api/login", json={"email": "x@y.z", "password": "pw"})
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"


def test_login_success(client, monkeypatch):
    good_hash = hashlib.md5(b"secret123").hexdigest()
    row = {
        "user_id": 12,
        "name": "API Test User",
        "email": "autotest@example.com",
        "password_hash": good_hash,
        "library_id": 1,
        "role_name": "Member",
    }
    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    r = client.post(
        "/api/login",
        json={"email": "autotest@example.com", "password": "secret123"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["user"]["user_id"] == 12
    assert body["user"]["role"] == "Member"
    assert body["user"]["library_id"] == 1


def test_logout_revokes_token(client, make_token):
    token = make_token(user_id=1, role="Member", library_id=1)
    ok = client.post("/api/logout", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    r = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.get_json()["error"] in {"token_revoked", "unauthorized"}


def test_refresh_token_ok(client, make_refresh_token):
    refresh_token = make_refresh_token(user_id=1, role="Member", library_id=1)
    r = client.post("/api/token/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert "access_token" in body


def test_refresh_with_access_token_fails(client, make_token):
    access_token = make_token(user_id=1, role="Member", library_id=1)
    r = client.post(
        "/api/token/refresh",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    # Depending on JWT library behavior -> 401 vagy 422 (fresh vs refresh mismatch)
    assert r.status_code in (401, 422)
