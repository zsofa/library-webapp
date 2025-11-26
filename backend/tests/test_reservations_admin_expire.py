import reservation_routes
from tests.conftest import make_get_db_cursor


def test_expire_reservations_forbidden_for_member(client, make_token):
    token = make_token(user_id=2, role="Member")
    r = client.post("/api/admin/reservations/expire", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_expire_reservations_ok(client, make_token, monkeypatch):
    returned = [{"reservation_id": 1}, {"reservation_id": 2}, {"reservation_id": 3}]
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchall=returned))
    admin = make_token(user_id=1, role="Admin")
    r = client.post("/api/admin/reservations/expire", headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 200
    assert r.get_json()["expired_count"] == 3


def test_expire_reservations_db_error(client, make_token, monkeypatch):
    monkeypatch.setattr(
        reservation_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True)
    )
    admin = make_token(user_id=1, role="Admin")
    r = client.post("/api/admin/reservations/expire", headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"
