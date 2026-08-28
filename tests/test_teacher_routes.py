from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.deps import get_teacher_workspace_store
from backend.core.config import get_settings
from backend.main import create_app
from backend.services.teacher_workspace import TeacherWorkspaceStore


def make_client(tmp_path):
    application = create_app()
    store = TeacherWorkspaceStore(
        db_file=tmp_path / "teacher_workspace.sqlite3",
        seed_file=Path(__file__).resolve().parents[1] / "data" / "teacher_workspace_seed.json",
    )
    application.dependency_overrides[get_teacher_workspace_store] = lambda: store
    return TestClient(application)


def test_alert_update_is_persisted_and_audited(tmp_path):
    client = make_client(tmp_path)
    workspace = client.get("/api/teacher/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["data"]["alerts"][0]["status"] == "new"
    revision = workspace.json()["revision"]

    update = client.patch(
        "/api/teacher/alerts/alert-1",
        json={"status": "resolved", "expectedRevision": revision},
    )
    assert update.status_code == 200
    assert update.json()["data"]["alert"]["status"] == "resolved"
    assert update.json()["data"]["audit"]["actorId"] == "local-teacher"

    reloaded = client.get("/api/teacher/workspace").json()["data"]
    assert next(item for item in reloaded["alerts"] if item["id"] == "alert-1")["status"] == "resolved"
    assert reloaded["auditTrail"][-1]["action"] == "alert_status_updated"


def test_draft_only_includes_unresolved_alerts_in_selected_class(tmp_path):
    client = make_client(tmp_path)
    revision = client.get("/api/teacher/workspace").json()["revision"]

    response = client.post(
        "/api/teacher/interventions/drafts",
        json={"classId": "telecom2401", "expectedRevision": revision},
    )
    assert response.status_code == 200
    draft = response.json()["data"]["intervention"]
    assert draft["classId"] == "telecom2401"
    assert set(draft["alertIds"]) == {"alert-2", "alert-4"}

    revision = response.json()["data"]["revision"]
    assigned = client.patch(
        f"/api/teacher/interventions/{draft['id']}",
        json={"status": "assigned", "expectedRevision": revision},
    )
    assert assigned.status_code == 200
    assert assigned.json()["data"]["intervention"]["status"] == "assigned"
    completed = client.patch(
        f"/api/teacher/interventions/{draft['id']}",
        json={"status": "completed", "expectedRevision": assigned.json()["data"]["revision"]},
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["intervention"]["completedAt"]


def test_stale_revision_is_rejected_without_overwriting_the_latest_change(tmp_path):
    client = make_client(tmp_path)
    initial_revision = client.get("/api/teacher/workspace").json()["revision"]

    first_update = client.patch(
        "/api/teacher/alerts/alert-1",
        json={"status": "in_progress", "expectedRevision": initial_revision},
    )
    assert first_update.status_code == 200

    stale_update = client.patch(
        "/api/teacher/alerts/alert-1",
        json={"status": "resolved", "expectedRevision": initial_revision},
    )
    assert stale_update.status_code == 409

    reloaded = client.get("/api/teacher/workspace").json()["data"]
    assert next(item for item in reloaded["alerts"] if item["id"] == "alert-1")["status"] == "in_progress"


def test_access_code_blocks_workspace_until_the_correct_code_is_sent(tmp_path, monkeypatch):
    monkeypatch.setenv("TEACHER_ACCESS_CODE", "local-pilot-2026")
    get_settings.cache_clear()
    try:
        client = make_client(tmp_path)
        assert client.get("/api/teacher/workspace").status_code == 401
        assert (
            client.patch(
                "/api/teacher/alerts/alert-1",
                json={"status": "in_progress", "expectedRevision": 1},
            ).status_code
            == 401
        )
        assert client.post("/api/teacher/session", json={"accessCode": "wrong"}).status_code == 401
        login = client.post(
            "/api/teacher/session", json={"accessCode": "local-pilot-2026"}
        )
        assert login.status_code == 200
        assert "HttpOnly" in login.headers["set-cookie"]
        assert client.get("/api/teacher/workspace").status_code == 200
        assert (
            client.patch(
                "/api/teacher/alerts/alert-1",
                json={"status": "in_progress", "expectedRevision": 1},
            ).status_code
            == 200
        )
    finally:
        get_settings.cache_clear()


def test_all_write_operations_require_the_current_revision(tmp_path):
    client = make_client(tmp_path)

    assert (
        client.patch("/api/teacher/alerts/alert-1", json={"status": "in_progress"}).status_code
        == 422
    )
    assert client.post("/api/teacher/interventions/drafts", json={"classId": "telecom2401"}).status_code == 422


def test_sqlite_store_persists_across_instances(tmp_path):
    seed = Path(__file__).resolve().parents[1] / "data" / "teacher_workspace_seed.json"
    database = tmp_path / "teacher.sqlite3"
    first = TeacherWorkspaceStore(database, seed)
    revision = first.read()["revision"]
    first.update_alert("alert-1", "resolved", get_local_actor(), revision)
    second = TeacherWorkspaceStore(database, seed)
    alert = next(item for item in second.read()["alerts"] if item["id"] == "alert-1")
    assert alert["status"] == "resolved"


def test_import_requires_live_data_and_is_audited(tmp_path):
    seed = Path(__file__).resolve().parents[1] / "data" / "teacher_workspace_seed.json"
    store = TeacherWorkspaceStore(tmp_path / "teacher.sqlite3", seed)
    workspace = store.read()
    try:
        store.import_live_workspace(workspace, get_local_actor(), workspace["revision"])
    except ValueError:
        pass
    else:
        raise AssertionError("demo data must not be imported as live data")
    workspace["dataSource"] = "live"
    _, audit, revision = store.import_live_workspace(
        workspace, get_local_actor(), workspace["revision"]
    )
    assert revision == workspace["revision"] + 1
    assert audit["action"] == "workspace_imported"


def get_local_actor():
    from backend.schemas.teacher import TeacherActor

    return TeacherActor(id="test-teacher", display_name="测试教师")
