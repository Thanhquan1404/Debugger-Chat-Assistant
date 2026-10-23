from fastapi.testclient import TestClient

from ai_debugger.main import create_app


def test_request_id_header_present(test_settings, fake_container):
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert "X-Request-ID" in r.headers
    assert r.headers["X-Request-ID"].startswith("req_")


def test_request_id_propagated(test_settings, fake_container):
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.get("/api/health", headers={"X-Request-ID": "req_custom_123"})
    assert r.headers["X-Request-ID"] == "req_custom_123"
