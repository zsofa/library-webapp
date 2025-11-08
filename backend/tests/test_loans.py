from datetime import date, datetime, timedelta, timezone

import loan_routes
from tests.conftest import FakeCursor, make_get_db_cursor


def test_create_loan_missing_fields(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_fields"


def test_create_loan_invalid_loan_days_type(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans",
        json={"item_id": 1, "loan_days": "abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_loan_days"


def test_create_loan_invalid_loan_days_value(client, make_token):
    token = make_token(user_id=1, role="Member")
    for val in (0, -3):
        r = client.post(
            "/api/loans",
            json={"item_id": 1, "loan_days": val},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400
        assert r.get_json()["error"] == "invalid_loan_days"


def test_create_loan_item_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans", json={"item_id": 999}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "item_not_found"


def test_create_loan_different_library(client, make_token, monkeypatch):
    item = {"item_id": 1, "book_id": 5, "library_id": 2}
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=item))
    token = make_token(user_id=1, role="Member", library_id=1)
    r = client.post("/api/loans", json={"item_id": 1}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "different_library"


def test_create_loan_item_already_loaned(client, make_token, monkeypatch):
    item = {"item_id": 1, "book_id": 5, "library_id": 1}
    active = {"loan_id": 7}
    seq = [item, active]
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=seq))
    token = make_token(user_id=1, role="Member", library_id=1)
    r = client.post("/api/loans", json={"item_id": 1}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409
    assert r.get_json()["error"] == "item_already_loaned"


def test_create_loan_success(client, make_token, monkeypatch):
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    due = date(2025, 1, 15)
    item = {"item_id": 1, "book_id": 5, "library_id": 1}
    inserted = {
        "loan_id": 123,
        "item_id": 1,
        "user_id": 1,
        "loan_date": now,
        "due_date": due,
        "return_date": None,
        "fine_paid": 0.0,
    }
    seq = [item, None, inserted]
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=seq))
    token = make_token(user_id=1, role="Member", library_id=1)
    r = client.post("/api/loans", json={"item_id": 1}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["loan_id"] == 123
    assert body["item_id"] == 1
    assert body["user_id"] == 1
    assert body["status"] == "active"


def test_create_loan_book_level_success(client, make_token, monkeypatch):
    """
    Book-level loan: DB sequence:
      1) Check book exists
      2) Pick free item (FOR UPDATE SKIP LOCKED or legacy LEFT JOIN)
      3) INSERT RETURNING loan
    """

    book_row = {"book_id": 5}
    free_item = {"item_id": 77, "book_id": 5, "library_id": 1}
    loan_insert = {
        "loan_id": 555,
        "loan_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "due_date": date(2025, 1, 11),
        "fine_paid": 0.0,
    }

    class Cursor(FakeCursor):
        def execute(self, sql, params=None):
            sql_lower = sql.lower()
            if "from book" in sql_lower:
                self._fetchone_single = book_row
            elif "from item" in sql_lower and (
                "for update" in sql_lower
                or "left join loan" in sql_lower
                or "not exists" in sql_lower
            ):
                # Support both new (FOR UPDATE SKIP LOCKED + NOT EXISTS)
                # and legacy LEFT JOIN query shapes
                self._fetchone_single = free_item
            elif "insert into loan" in sql_lower:
                self._fetchone_single = loan_insert

    class CM:
        def __enter__(self):
            return Cursor()

        def __exit__(self, exc_type, exc, tb):
            return False

    def _get_db_cursor(commit: bool = False):
        return CM()

    monkeypatch.setattr(loan_routes, "get_db_cursor", _get_db_cursor)

    token = make_token(user_id=1, role="Member", library_id=1)
    r = client.post(
        "/api/loans",
        json={"book_id": 5, "loan_days": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body["loan_id"] == 555
    assert body["book_id"] == 5
    assert body["item_id"] == 77
    assert body["status"] == "active"


def test_create_loan_db_error(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True))
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans", json={"item_id": 1}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"


def test_return_loan_success(client, make_token, monkeypatch):
    now = datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc)
    updated = {
        "loan_id": 123,
        "item_id": 1,
        "user_id": 1,
        "loan_date": now - timedelta(days=1),
        "due_date": date(2025, 1, 15),
        "return_date": now,
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(
        loan_routes,
        "get_db_cursor",
        make_get_db_cursor(fetchone=[{**updated, "return_date": None}, updated]),
    )
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans/123/return", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["loan_id"] == 123


def test_return_loan_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans/999999/return", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
    assert r.get_json()["error"] == "loan_not_found"


def test_return_loan_already_returned(client, make_token, monkeypatch):
    row = {
        "loan_id": 123,
        "item_id": 1,
        "user_id": 1,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=1),
        "due_date": date.today() + timedelta(days=10),
        "return_date": datetime.now(timezone.utc),
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans/123/return", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "loan_already_returned"


def test_return_loan_forbidden_other_users_loan(client, make_token, monkeypatch):
    row = {
        "loan_id": 123,
        "item_id": 1,
        "user_id": 99,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=1),
        "due_date": date.today() + timedelta(days=10),
        "return_date": None,
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans/123/return", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_extend_loan_invalid_extra_days(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans/1/extend", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_extra_days"

    r = client.post(
        "/api/loans/1/extend",
        json={"extra_days": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400

    r = client.post(
        "/api/loans/1/extend", json={"extra_days": 0}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400


def test_extend_loan_not_found(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans/999/extend",
        json={"extra_days": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "loan_not_found"


def test_extend_loan_overdue_blocked(client, make_token, monkeypatch):
    past_due = date.today() - timedelta(days=1)
    row = {
        "loan_id": 1,
        "item_id": 1,
        "user_id": 1,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=10),
        "due_date": past_due,
        "return_date": None,
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans/1/extend", json={"extra_days": 7}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "loan_overdue"


def test_extend_loan_already_returned(client, make_token, monkeypatch):
    row = {
        "loan_id": 1,
        "item_id": 1,
        "user_id": 1,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=2),
        "due_date": date.today() + timedelta(days=5),
        "return_date": datetime.now(timezone.utc),
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans/1/extend", json={"extra_days": 7}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "loan_already_returned"


def test_extend_loan_forbidden_other_users_loan(client, make_token, monkeypatch):
    row = {
        "loan_id": 1,
        "item_id": 1,
        "user_id": 99,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=2),
        "due_date": date.today() + timedelta(days=5),
        "return_date": None,
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans/1/extend", json={"extra_days": 7}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_extend_loan_success(client, make_token, monkeypatch):
    today = date.today()
    row_before = {
        "loan_id": 1,
        "item_id": 1,
        "user_id": 1,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=2),
        "due_date": today + timedelta(days=5),
        "return_date": None,
        "fine_paid": 0.0,
    }
    row_after = {
        "loan_id": 1,
        "item_id": 1,
        "user_id": 1,
        "loan_date": row_before["loan_date"],
        "due_date": row_before["due_date"] + timedelta(days=7),
        "return_date": None,
        "fine_paid": 0.0,
    }
    monkeypatch.setattr(
        loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=[row_before, row_after])
    )
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans/1/extend", json={"extra_days": 7}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.get_json()["due_date"] == row_after["due_date"].isoformat()


def test_list_loans_for_user_self_ok(client, make_token, monkeypatch):
    rows = [
        {
            "loan_id": 10,
            "item_id": 1,
            "user_id": 2,
            "loan_date": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            "due_date": date(2025, 1, 15),
            "return_date": None,
            "fine_paid": 0.0,
        }
    ]
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchall=rows))
    token = make_token(user_id=2, role="Member")
    r = client.get("/api/users/2/loans?active=true", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert body[0]["loan_id"] == 10
    assert body[0]["return_date"] is None


def test_list_loans_for_user_forbidden_other(client, make_token):
    token = make_token(user_id=2, role="Member")
    r = client.get("/api/users/3/loans", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_list_loans_for_user_admin_ok(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchall=[]))
    token = make_token(user_id=1, role="Admin")
    r = client.get("/api/users/999/loans", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_overdue_loans_forbidden_for_member(client, make_token):
    token = make_token(user_id=1, role="Member")
    r = client.get("/api/loans/overdue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_list_overdue_loans_admin_ok(client, make_token, monkeypatch):
    rows = [
        {
            "loan_id": 11,
            "item_id": 3,
            "user_id": 2,
            "loan_date": datetime(2024, 12, 1, 12, 0, tzinfo=timezone.utc),
            "due_date": date(2024, 12, 20),
            "return_date": None,
            "fine_paid": 0.0,
        }
    ]
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(fetchall=rows))
    token = make_token(user_id=1, role="Admin")
    r = client.get("/api/loans/overdue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()[0]["loan_id"] == 11


def test_return_loan_db_error(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True))
    token = make_token(user_id=1, role="Member")
    r = client.post("/api/loans/1/return", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"


def test_extend_loan_db_error(client, make_token, monkeypatch):
    monkeypatch.setattr(loan_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True))
    token = make_token(user_id=1, role="Member")
    r = client.post(
        "/api/loans/1/extend", json={"extra_days": 5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"


def test_admin_can_return_others_loan(client, make_token, monkeypatch):
    row_before = {
        "loan_id": 10,
        "item_id": 1,
        "user_id": 99,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=1),
        "due_date": date.today() + timedelta(days=5),
        "return_date": None,
        "fine_paid": 0.0,
    }
    row_after = {**row_before, "return_date": datetime.now(timezone.utc)}
    monkeypatch.setattr(
        loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=[row_before, row_after])
    )
    admin_token = make_token(user_id=1, role="Admin")
    r = client.post("/api/loans/10/return", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.get_json()["loan_id"] == 10


def test_admin_can_extend_others_loan(client, make_token, monkeypatch):
    today = date.today()
    row_before = {
        "loan_id": 10,
        "item_id": 1,
        "user_id": 99,
        "loan_date": datetime.now(timezone.utc) - timedelta(days=2),
        "due_date": today + timedelta(days=3),
        "return_date": None,
        "fine_paid": 0.0,
    }
    row_after = {**row_before, "due_date": row_before["due_date"] + timedelta(days=7)}
    monkeypatch.setattr(
        loan_routes, "get_db_cursor", make_get_db_cursor(fetchone=[row_before, row_after])
    )
    admin_token = make_token(user_id=1, role="Admin")
    r = client.post(
        "/api/loans/10/extend",
        json={"extra_days": 7},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.get_json()["due_date"] == row_after["due_date"].isoformat()
