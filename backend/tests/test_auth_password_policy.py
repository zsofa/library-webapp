import auth_routes
from password_utils import hash_password
from tests.conftest import make_get_db_cursor


def test_register_weak_password(client):
    payload = {
        "email": "weak@example.com",
        "password": "abc",  # gyenge
        "name": "Weak User",
        "address": "Addr",
        "date_of_birth": "2000-01-01",
    }
    r = client.post("/api/register", json=payload)
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "weak_password"
    assert "violations" in body.get("meta", {})


def test_change_password_missing_fields(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/me/password", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_fields"


def test_change_password_wrong_old(client, make_token, monkeypatch):
    row = {"password_hash": hash_password("correct-old")}
    monkeypatch.setattr(auth_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/me/password",
        json={"old_password": "wrong-old", "new_password": "Newpass123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.get_json()["error"] == "invalid_credentials"


def test_change_password_weak_new(client, make_token, monkeypatch):
    row = {"password_hash": hash_password("correct-old")}
    calls = {"n": 0}

    class TwoStage:
        def __enter__(self):
            calls["n"] += 1
            if calls["n"] == 1:
                return type(
                    "C", (), {"execute": lambda *a, **k: None, "fetchone": lambda self=None: row}
                )()
            return type(
                "C2", (), {"execute": lambda *a, **k: None, "fetchone": lambda self=None: None}
            )()

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(auth_routes, "get_db_cursor", lambda commit=False: TwoStage())

    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/me/password",
        json={"old_password": "correct-old", "new_password": "weak"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "weak_password"


def test_change_password_success(client, make_token, monkeypatch):
    row = {"password_hash": hash_password("correct-old")}
    calls = {"n": 0}

    class TwoStage:
        def __enter__(self):
            calls["n"] += 1
            if calls["n"] == 1:
                return type(
                    "C", (), {"execute": lambda *a, **k: None, "fetchone": lambda self=None: row}
                )()
            return type(
                "C2", (), {"execute": lambda *a, **k: None, "fetchone": lambda self=None: None}
            )()

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(auth_routes, "get_db_cursor", lambda commit=False: TwoStage())

    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/me/password",
        json={"old_password": "correct-old", "new_password": "Newpass123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
