import admin_routes
from tests.conftest import make_get_db_cursor


def test_admin_stats_forbidden_for_member(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_admin_stats_ok(client, make_token, monkeypatch):
    row = {
        "total_users": 10,
        "active_users": 9,
        "total_books": 100,
        "total_items": 180,
        "active_loans": 5,
        "overdue_loans": 2,
        "total_reservations": 7,
    }
    monkeypatch.setattr(admin_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    admin_token = make_token(user_id=1, role="Admin")
    r = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["total_users"] == 10
    assert body["overdue_loans"] == 2


def test_admin_stats_db_error(client, make_token, monkeypatch):
    monkeypatch.setattr(admin_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True))
    admin_token = make_token(user_id=1, role="Admin")
    r = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"
