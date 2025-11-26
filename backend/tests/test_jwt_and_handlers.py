def test_me_returns_claims(client, make_token):
    token = make_token(user_id=42, role="Member", library_id=7)
    r = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["user_id"] == 42
    assert body["role"] == "Member"
    assert body["library_id"] == 7


def test_protected_without_token_unauthorized(client):
    r = client.get("/api/users/1")
    assert r.status_code == 401
    body = r.get_json()
    assert body["error"] == "unauthorized"
    # request_id injected?
    assert "meta" in body and "request_id" in body["meta"]


def test_protected_with_invalid_token_unauthorized(client):
    r = client.get("/api/users/1", headers={"Authorization": "Bearer invalid"})
    assert r.status_code == 401
    # token_expired vagy token_revoked előfordulhat más esetekben – itt elég a halmaz ellenőrzése
    assert r.get_json()["error"] in {"unauthorized", "token_expired", "token_revoked"}


def test_404_handler(client):
    r = client.get("/api/this/does/not/exist")
    assert r.status_code == 404
    body = r.get_json()
    assert body["error"] == "not_found"
    assert "meta" in body and "request_id" in body["meta"]
