from datetime import date, datetime, timezone

from psycopg2.errors import UniqueViolation

import reservation_routes
from tests.conftest import FakeCursor, make_get_db_cursor


def test_create_reservation_missing_fields(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/reservations", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_fields"


def test_create_reservation_invalid_ids(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/reservations", json={"book_id": "x"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_ids"


def test_create_reservation_user_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    token = make_token(user_id=999, role="Member")
    r = client.post(
        "/api/reservations", json={"book_id": 5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "user_not_found"


def test_create_reservation_book_not_found(client, make_token, monkeypatch):
    seq = [{"user_id": 1}, None]
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=seq))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/reservations", json={"book_id": 5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "book_not_found"


def test_create_reservation_exists(client, make_token, monkeypatch):
    # pending already exists
    seq = [{"user_id": 1}, {"book_id": 5}, {"reservation_id": 777}]
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=seq))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/reservations", json={"book_id": 5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 409
    assert r.get_json()["error"] == "reservation_exists"


def test_create_reservation_success(client, make_token, monkeypatch):
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    seq = [
        {"user_id": 1},  # user ok
        {"book_id": 5},  # book ok
        None,  # existing active reservation check returns None (no pending/ready)
        {"next_pos": 2},  # queue next
        {
            "reservation_id": 123,
            "reservation_date": now,
            "expiry_date": date(2025, 1, 8),
            "status": "pending",
        },
    ]
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=seq))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/reservations", json={"book_id": 5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body["reservation_id"] == 123
    assert body["queue_number"] == 2
    assert body["status"] == "pending"


def test_create_reservation_retry_on_queue_conflict(client, make_token, monkeypatch):
    """
    Emulate a queue_number UNIQUE violation on first insert, success on second.
    We simulate user+book existence, then queue MAX(...)+1, then first INSERT raises
    UniqueViolation, second attempt returns row.
    """

    class Cursor(FakeCursor):
        def __init__(self):
            super().__init__()
            self.step = 0
            self._fetchone_single = None

        def execute(self, sql, params=None):
            sl = sql.lower()
            if "from app_user" in sl:
                self._fetchone_single = {"user_id": 1}
            elif "from book" in sl:
                self._fetchone_single = {"book_id": 5}
            elif "status in" in sl:
                # existing active reservation check
                self._fetchone_single = None
            elif "for update" in sl and "reservation" in sl:
                # lock existing rows
                self._fetchone_single = None
            elif "select coalesce(max(queue_number)" in sl:
                self._fetchone_single = {"next_pos": 3}
            elif "insert into reservation" in sl:
                self.step += 1
                if self.step == 1:
                    raise UniqueViolation()
                else:
                    self._fetchone_single = {
                        "reservation_id": 999,
                        "reservation_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                        "expiry_date": date(2025, 1, 8),
                        "status": "pending",
                    }

    class CM:
        def __enter__(self):
            return Cursor()

        def __exit__(self, exc_type, exc, tb):
            return False

    def _get_db_cursor(commit=True):
        return CM()

    monkeypatch.setattr(reservation_routes, "get_db_cursor", _get_db_cursor)

    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/reservations", json={"book_id": 5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body["reservation_id"] == 999
    assert body["queue_number"] == 3
    assert body["status"] == "pending"


def test_list_reservations_for_user_forbidden_other(client, make_token):
    token = make_token(user_id=2, role="Member")
    r = client.get("/api/users/3/reservations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_list_reservations_for_user_invalid_status(client, make_token):
    token = make_token(user_id=2, role="Member")
    r = client.get(
        "/api/users/2/reservations?status=unknown", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_status"


def test_list_reservations_for_user_ok(client, make_token, monkeypatch):
    rows = [
        {
            "reservation_id": 1,
            "book_id": 5,
            "user_id": 2,
            "queue_number": 1,
            "reservation_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            "expiry_date": date(2025, 1, 8),
            "status": "pending",
        }
    ]
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchall=rows))
    token = make_token(user_id=2, role="Member")
    r = client.get(
        "/api/users/2/reservations?status=all", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body[0]["reservation_id"] == 1
    assert body[0]["status"] == "pending"


def test_list_reservations_for_book_forbidden_for_member(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.get("/api/books/5/reservations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_list_reservations_for_book_admin_ok(client, make_token, monkeypatch):
    rows = [
        {
            "reservation_id": 1,
            "book_id": 5,
            "user_id": 2,
            "queue_number": 1,
            "reservation_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            "expiry_date": date(2025, 1, 8),
            "status": "pending",
        }
    ]
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchall=rows))
    token = make_token(user_id=1, role="Admin")
    r = client.get("/api/books/5/reservations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()[0]["reservation_id"] == 1


def test_update_reservation_status_invalid_status(client, make_token):
    admin_token = make_token(user_id=1, role="Admin")
    r = client.post(
        "/api/reservations/1/status",
        json={"status": "invalid"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_status"


def test_update_reservation_status_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    admin_token = make_token(user_id=1, role="Admin")
    r = client.post(
        "/api/reservations/999/status",
        json={"status": "ready"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "reservation_not_found"


def test_update_reservation_status_success(client, make_token, monkeypatch):
    after = {
        "reservation_id": 1,
        "book_id": 5,
        "user_id": 2,
        "queue_number": 1,
        "reservation_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "expiry_date": date(2025, 1, 8),
        "status": "ready",
    }
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=after))
    admin_token = make_token(user_id=1, role="Admin")
    r = client.post(
        "/api/reservations/1/status",
        json={"status": "ready"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.get_json()["status"] == "ready"


def test_cancel_reservation_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    token = make_token(user_id=2, role="Member")
    r = client.post("/api/reservations/999/cancel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
    assert r.get_json()["error"] == "reservation_not_found"


def test_cancel_reservation_forbidden_other_users_reservation(client, make_token, monkeypatch):
    row = {"reservation_id": 1, "user_id": 3}
    monkeypatch.setattr(reservation_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=2, role="Member")
    r = client.post("/api/reservations/1/cancel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_cancel_reservation_success_sets_expired(client, make_token, monkeypatch):
    lookup = {"reservation_id": 1, "user_id": 2}
    updated = {
        "reservation_id": 1,
        "book_id": 5,
        "user_id": 2,
        "queue_number": 1,
        "reservation_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "expiry_date": date(2025, 1, 8),
        "status": "expired",
    }
    calls = {"n": 0}

    class TwoStageCM:
        def __enter__(self):
            calls["n"] += 1
            if calls["n"] == 1:
                return FakeCursor(fetchone=lookup)
            return FakeCursor(fetchone=updated)

        def __exit__(self, exc_type, exc, tb):
            return False

    def _two_stage_get_db_cursor(commit: bool = False):
        return TwoStageCM()

    monkeypatch.setattr(reservation_routes, "get_db_cursor", _two_stage_get_db_cursor)
    token = make_token(user_id=2, role="Member")
    r = client.post("/api/reservations/1/cancel", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "expired"


def test_admin_can_cancel_others_reservation(client, make_token, monkeypatch):
    lookup = {"reservation_id": 1, "user_id": 99}
    updated = {
        "reservation_id": 1,
        "book_id": 5,
        "user_id": 99,
        "queue_number": 1,
        "reservation_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "expiry_date": date(2025, 1, 8),
        "status": "expired",
    }
    calls = {"n": 0}

    class TwoStageCM:
        def __enter__(self):
            calls["n"] += 1
            if calls["n"] == 1:
                return FakeCursor(fetchone=lookup)
            return FakeCursor(fetchone=updated)

        def __exit__(self, exc_type, exc, tb):
            return False

    def _two_stage_get_db_cursor(commit: bool = False):
        return TwoStageCM()

    monkeypatch.setattr(reservation_routes, "get_db_cursor", _two_stage_get_db_cursor)
    admin_token = make_token(user_id=1, role="Admin")
    r = client.post(
        "/api/reservations/1/cancel", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert r.status_code == 200
    assert r.get_json()["status"] == "expired"
