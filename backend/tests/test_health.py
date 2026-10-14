from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_returns_ok():
    """Verify that GET /api/health returns 200 with expected structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["service"] == "ai-code-debugger-backend"
    assert "timestamp" in data

def test_cors_headers_present():
    """Verify CORS headers when request originates from allowed frontend origin."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
