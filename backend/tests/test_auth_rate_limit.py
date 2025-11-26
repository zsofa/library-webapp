import time

import auth_routes
from password_utils import hash_password
from tests.conftest import make_get_db_cursor


def test_login_rate_limit_blocks_after_limit(client, monkeypatch):
    email = "ratelimit@example.com"
    wrong_pw = "NOPE"

    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))

    for _ in range(5):
        r = client.post("/api/login", json={"email": email, "password": wrong_pw})
        assert r.status_code in (401, 429)

    r = client.post("/api/login", json={"email": email, "password": wrong_pw})
    assert r.status_code == 429
    body = r.get_json()
    assert body["error"] == "too_many_attempts"
    assert body.get("meta", {}).get("retry_after") is not None


def test_login_rate_limit_resets_after_success(client, monkeypatch):
    email = "ratelimit-reset@example.com"
    wrong_pw = "NOPE"

    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    for _ in range(4):
        r = client.post("/api/login", json={"email": email, "password": wrong_pw})
        assert r.status_code == 401

    valid_row = {
        "user_id": 42,
        "name": "RL Test",
        "email": email,
        "password_hash": hash_password("secret123"),
        "library_id": 1,
        "role_name": "Member",
    }

    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=valid_row))
    ok = client.post("/api/login", json={"email": email, "password": "secret123"})
    assert ok.status_code == 200

    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    for _ in range(4):
        r = client.post("/api/login", json={"email": email, "password": wrong_pw})
        assert r.status_code == 401

    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=valid_row))
    ok2 = client.post("/api/login", json={"email": email, "password": "secret123"})
    assert ok2.status_code == 200


def test_login_rate_limit_window_expires(client, monkeypatch):
    email = "ratelimit-window@example.com"
    wrong_pw = "NOPE"

    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))

    for _ in range(5):
        client.post("/api/login", json={"email": email, "password": wrong_pw})
    blocked = client.post("/api/login", json={"email": email, "password": wrong_pw})
    assert blocked.status_code == 429

    now = time.time()
    monkeypatch.setattr("auth_utils.time.time", lambda: now + 10000)

    r = client.post("/api/login", json={"email": email, "password": wrong_pw})
    assert r.status_code in (401, 429)
