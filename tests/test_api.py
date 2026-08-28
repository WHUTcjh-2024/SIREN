from fastapi.testclient import TestClient

from backend.main import app, create_app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.json() == {"status": "ok", "service": "siren-api"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


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


def test_analysis_rejects_multiple_or_invalid_images():
    multiple = client.post(
        "/api/laser-diffraction",
        files=[("images", ("a.png", b"x", "image/png")), ("images", ("b.png", b"x", "image/png"))],
    )
    assert multiple.status_code == 400
    invalid = client.post(
        "/api/laser-diffraction", files={"images": ("a.png", b"not-an-image", "image/png")}
    )
    assert invalid.status_code == 415


def test_client_cannot_choose_experiment_session_id():
    response = client.post(
        "/api/experiment-state", json={"sid": "chosen", "state": {"progress": 1}}
    )
    assert response.status_code == 422


def test_invalid_experiment_cookie_is_replaced_with_server_generated_id():
    cookie_client = TestClient(app)
    cookie_client.cookies.set("exp_sid", "malicious; Path=/")
    response = cookie_client.post("/api/experiment-state", json={"state": {"progress": 1}})
    assert response.status_code == 200
    cookie = response.cookies.get("exp_sid")
    assert cookie is not None
    assert cookie != "malicious; Path=/"


def test_request_body_limit_rejects_oversized_content_length():
    response = client.post(
        "/api/experiment-state",
        content=b"{}",
        headers={"Content-Length": str(32 * 1024 * 1024)},
    )
    assert response.status_code == 413
