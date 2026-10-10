from fastapi.testclient import TestClient

from ai_debugger.main import create_app


def test_health_envelope(test_settings, fake_container):
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert "message" in body["data"]
    assert "Welcome" in body["data"]["message"]
    assert "version" in body["data"]
