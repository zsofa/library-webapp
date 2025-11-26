import book_routes
from tests.conftest import make_get_db_cursor


def test_books_list_transform(client, monkeypatch):
    rows = [
        {
            "book_id": 5,
            "title": "Foundation",
            "author": "Isaac Asimov",
            "isbn": "978",
            "publication_year": 1951,
            "category": "Sci-fi",
            "total_items": 2,
            "loaned_items": 1,
        }
    ]
    monkeypatch.setattr(book_routes, "get_db_cursor", make_get_db_cursor(fetchall=rows))
    r = client.get("/api/books?q=dune&category=Sci-fi")
    assert r.status_code == 200
    body = r.get_json()
    assert body[0]["available_items"] == 1
    assert body[0]["total_items"] == 2


def test_books_get_not_found(client, monkeypatch):
    monkeypatch.setattr(book_routes, "get_db_cursor", make_get_db_cursor(fetchone=None))
    r = client.get("/api/books/999999")
    assert r.status_code == 404
    assert r.get_json()["error"] == "book_not_found"


def test_books_get_success(client, monkeypatch):
    row = {
        "book_id": 5,
        "title": "Foundation",
        "author": "Isaac Asimov",
        "isbn": "978",
        "publication_year": 1951,
        "category": "Sci-fi",
        "total_items": 2,
        "loaned_items": 1,
    }
    monkeypatch.setattr(book_routes, "get_db_cursor", make_get_db_cursor(fetchone=row))
    r = client.get("/api/books/5")
    assert r.status_code == 200
    body = r.get_json()
    assert body["available_items"] == 1
    assert body["book_id"] == 5


def test_books_list_db_error(client, monkeypatch):
    monkeypatch.setattr(book_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True))
    r = client.get("/api/books?q=x")
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"


def test_books_get_db_error(client, monkeypatch):
    monkeypatch.setattr(book_routes, "get_db_cursor", make_get_db_cursor(raise_on_enter=True))
    r = client.get("/api/books/1")
    assert r.status_code == 500
    assert r.get_json()["error"] == "db_error"
