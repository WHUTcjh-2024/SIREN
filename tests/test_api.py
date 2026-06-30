from fastapi.testclient import TestClient

from backend.main import app, create_app


client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok", "service": "siren-api"}


def test_vue_spa_is_served_by_fastapi(tmp_path):
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<h1>SIREN</h1>", encoding="utf-8")

    response = TestClient(create_app(frontend_dist=frontend_dist)).get("/")
    assert response.status_code == 200
    assert "SIREN" in response.text


def test_calculate_validates_input():
    response = client.post("/api/calculate", json={"f": -1})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_agent_requires_external_key(monkeypatch):
    response = client.post("/api/ask", json={"question": "什么是衍射？"})
    assert response.status_code == 503
