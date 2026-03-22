"""Health endpoint tests."""


def test_health_returns_ok(client):
    """Health endpoint should return status and version."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert "checks" in data


def test_health_checks_database(client):
    """Health should report database status."""
    response = client.get("/api/health")
    data = response.json()
    assert data["checks"]["database"] == "connected"
