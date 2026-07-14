from app import app


def test_protected_routes_require_api_key(monkeypatch):
    monkeypatch.setenv("CONTENT_BOT_REQUIRE_AUTH", "true")
    monkeypatch.setenv("CONTENT_BOT_API_KEY", "test-secret")
    with app.test_client() as client:
        for method, path in [("get", "/status"), ("get", "/draft"), ("post", "/run")]:
            response = getattr(client, method)(path)
            assert response.status_code == 401


def test_valid_api_key_can_read_status(monkeypatch):
    monkeypatch.setenv("CONTENT_BOT_REQUIRE_AUTH", "true")
    monkeypatch.setenv("CONTENT_BOT_API_KEY", "test-secret")
    with app.test_client() as client:
        response = client.get("/status", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200


def test_health_remains_public(monkeypatch):
    monkeypatch.setenv("CONTENT_BOT_REQUIRE_AUTH", "true")
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
