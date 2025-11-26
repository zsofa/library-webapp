from datetime import date

import user_routes
from tests.conftest import make_get_db_cursor


def test_get_user_forbidden_for_other_member(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.get("/api/users/999999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_get_user_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(user_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    admin_token = make_token(user_id=1, role="Admin")
    r = client.get("/api/users/999999", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 404
    assert r.get_json()["error"] == "user_not_found"


def test_get_user_success(client, make_token, monkeypatch):
    dob = date(2000, 1, 1)
    row = {
        "user_id": 1,
        "email": "u@e.m",
        "name": "User",
        "address": "Addr",
        "date_of_birth": dob,
        "library_id": 1,
        "role_name": "Member",
    }
    monkeypatch.setattr(user_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.get("/api/users/1", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["user_id"] == 1
    assert body["date_of_birth"] == dob.isoformat()
    assert body["role"] == "Member"


def test_update_user_forbidden_for_other_member(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.put("/api/users/2", json={"name": "X"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_update_user_no_fields(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.put("/api/users/1", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "no_fields_to_update"


def test_update_user_invalid_dob(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.put(
        "/api/users/1",
        json={"date_of_birth": "31-12-1999"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_date_of_birth"


def test_update_user_success(client, make_token, monkeypatch):
    dob = date(1999, 12, 31)
    row = {
        "user_id": 1,
        "email": "u@e.m",
        "name": "Updated",
        "address": "New Addr",
        "date_of_birth": dob,
        "library_id": 1,
        "role_name": "Member",
    }
    monkeypatch.setattr(user_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.put(
        "/api/users/1",
        json={"name": "Updated", "address": "New Addr", "date_of_birth": "1999-12-31"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["name"] == "Updated"
    assert body["date_of_birth"] == "1999-12-31"


def test_update_other_user_as_admin_success(client, make_token, monkeypatch):
    dob = date(1990, 5, 5)
    row = {
        "user_id": 2,
        "email": "x@y.z",
        "name": "AdminUpdated",
        "address": "Addr",
        "date_of_birth": dob,
        "library_id": 1,
        "role_name": "Member",
    }
    monkeypatch.setattr(user_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Admin")
    r = client.put(
        "/api/users/2",
        json={"name": "AdminUpdated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.get_json()["name"] == "AdminUpdated"


def test_update_user_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(user_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    admin_token = make_token(user_id=1, role="Admin")
    r = client.put(
        "/api/users/999999",
        json={"name": "x"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "user_not_found"
