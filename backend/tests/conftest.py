import pytest
from flask_jwt_extended import create_access_token, create_refresh_token

from app import create_app

# A route modulok saját importtal hozzák a get_db_cursor-t, ezért modulonként monkeypatch-elünk,
# de a segédfüggvény (make_get_db_cursor) és FakeCursor globálisan itt elérhető.


class FakeCursor:
    """
    Egyszerű fake DB cursor:
    - execute: no-op (teszt specifikus override nélkül)
    - fetchone: ha listával inicializáltuk, sorban adja vissza az elemeket, különben mindig ugyanazt
    - fetchall: fix listát ad vissza
    """

    def __init__(self, fetchone=None, fetchall=None):
        self._fetchall = fetchall or []
        if isinstance(fetchone, list):
            self._fetchone_iter = iter(fetchone)
            self._fetchone_single = None
        else:
            self._fetchone_iter = None
            self._fetchone_single = fetchone

    def execute(self, *_args, **_kwargs):
        pass  # SQL nem kerül kiértékelésre

    def fetchone(self):
        if self._fetchone_iter is not None:
            try:
                return next(self._fetchone_iter)
            except StopIteration:
                return None
        return self._fetchone_single

    def fetchall(self):
        return self._fetchall


def make_get_db_cursor(fetchone=None, fetchall=None, raise_on_enter=False):
    """
    Visszaad egy get_db_cursor-szerű context managert (amit monkeypatch-elünk a route modulokban).
    """

    class _CM:
        def __enter__(self):
            if raise_on_enter:
                raise Exception("Simulated DB error")
            return FakeCursor(fetchone=fetchone, fetchall=fetchall)

        def __exit__(self, exc_type, exc, tb):
            return False  # ne nyeljük el a kivételeket

    def _get_db_cursor(commit: bool = False):
        return _CM()

    return _get_db_cursor


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_token(app):
    """
    JWT token generátor a tesztekhez.
    identity: user_id (stringként),
    claims: role, library_id
    """

    def _make(user_id: int, role: str = "Member", library_id: int = 1) -> str:
        with app.app_context():
            return create_access_token(
                identity=str(user_id),
                additional_claims={
                    "role": role,
                    "library_id": library_id,
                },
            )

    return _make


@pytest.fixture
def make_refresh_token(app):
    """
    Refresh JWT generátor tesztekhez (refresh endpoint tesztelésére).
    """

    def _make(user_id: int, role: str = "Member", library_id: int = 1) -> str:
        with app.app_context():
            return create_refresh_token(
                identity=str(user_id),
                additional_claims={
                    "role": role,
                    "library_id": library_id,
                },
            )

    return _make
