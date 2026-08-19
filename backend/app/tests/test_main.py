from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_status_code():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_body():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}