from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["server"]["status"] == "ok"
    # Check db status based on mock setup
    assert data["database"]["status"] == "ok" # Assumes mock allows success

def test_ping(client: TestClient):
    response = client.get("/health/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}