def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_openapi_served_or_404(client):
    """
    If openapi.yaml present in root, expect 200; else 404.
    Both behaviors acceptable; we just assert structured JSON error on 404.
    """
    r = client.get("/api/openapi.yaml")
    if r.status_code == 200:
        assert b"openapi:" in r.data  # YAML content
    else:
        assert r.status_code == 404
        body = r.get_json()
        assert body["error"] == "not_found"
