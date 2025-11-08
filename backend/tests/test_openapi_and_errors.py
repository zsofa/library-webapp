def test_invalid_token_has_request_id_meta(client):
    r = client.get("/api/me", headers={"Authorization": "Bearer invalid"})
    assert r.status_code == 401
    body = r.get_json()
    assert "meta" in body and "request_id" in body["meta"]


def test_404_has_request_id_meta(client):
    r = client.get("/api/unknown/route/xyz")
    assert r.status_code == 404
    body = r.get_json()
    assert body["error"] == "not_found"
    assert "meta" in body and "request_id" in body["meta"]
