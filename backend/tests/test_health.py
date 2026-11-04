from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Visa Assistant API"


def test_ready_reports_each_dependency(client: TestClient) -> None:
    # No Postgres in unit tests → degraded with per-check detail.
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 503
    assert set(r.json()["checks"]) == {"database", "redis"}


def test_cross_site_post_is_rejected(client: TestClient) -> None:
    r = client.post("/api/v1/health", headers={"origin": "https://evil.example"})
    assert r.status_code == 403
