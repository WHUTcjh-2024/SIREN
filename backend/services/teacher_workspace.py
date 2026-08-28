import copy
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator

from backend.schemas.teacher import AlertStatus, TeacherActor, TeacherWorkspaceData, WorkflowStatus


class WorkspaceRevisionConflict(RuntimeError):
    """Raised when a write is based on a stale workspace revision."""


Mutation = Callable[[dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]


class TeacherWorkspaceStore:
    """Transactional SQLite store for one local pilot workspace."""

    def __init__(self, db_file: Path, seed_file: Path, legacy_file: Path | None = None):
        self.db_file = db_file
        self.seed_file = seed_file
        self.legacy_file = legacy_file
        self._initialize()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_file, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("教师工作区数据不可读取") from exc
        if not isinstance(value, dict):
            raise RuntimeError("教师工作区数据格式无效")
        return value

    @staticmethod
    def _validate(state: dict[str, Any]) -> dict[str, Any]:
        try:
            return TeacherWorkspaceData.model_validate(state).model_dump(
                by_alias=True, mode="json"
            )
        except ValueError as exc:
            raise RuntimeError("教师工作区数据格式无效") from exc

    def _initial_state(self) -> dict[str, Any]:
        source = self.legacy_file if self.legacy_file and self.legacy_file.is_file() else self.seed_file
        if not source.is_file():
            raise RuntimeError("教师工作区种子数据不存在")
        previous = self._read_json(source)
        if "dataProfile" in previous:
            return self._validate(previous)
        seed = self._read_json(self.seed_file)
        statuses = {
            item.get("id"): item.get("status")
            for item in previous.get("alerts", [])
            if item.get("status") in {"new", "in_progress", "resolved"}
        }
        for alert in seed.get("alerts", []):
            if alert.get("id") in statuses:
                alert["status"] = statuses[alert["id"]]
        seed["interventions"] = previous.get("interventions", [])
        seed["auditTrail"] = previous.get("auditTrail", [])[-200:]
        seed["revision"] = max(int(seed.get("revision", 0)), int(previous.get("revision", 0)))
        return self._validate(seed)

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS teacher_workspace ("
                    "singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                    "revision INTEGER NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)"
                )
                if connection.execute("SELECT 1 FROM teacher_workspace").fetchone() is None:
                    state = self._initial_state()
                    connection.execute(
                        "INSERT OR IGNORE INTO teacher_workspace VALUES (1, ?, ?, ?)",
                        (state["revision"], self._serialize(state), self._timestamp()),
                    )
                connection.commit()
        except sqlite3.Error as exc:
            raise RuntimeError("教师工作区数据库不可用") from exc

    @staticmethod
    def _serialize(state: dict[str, Any]) -> str:
        return json.dumps(state, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _state(row: sqlite3.Row | None) -> dict[str, Any]:
        if row is None:
            raise RuntimeError("教师工作区尚未初始化")
        try:
            state = json.loads(row["payload"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("教师工作区数据库内容损坏") from exc
        if not isinstance(state, dict) or int(state.get("revision", -1)) != row["revision"]:
            raise RuntimeError("教师工作区版本信息不一致")
        return state

    @staticmethod
    def _append_audit(
        state: dict[str, Any], actor: TeacherActor, action: str, entity_id: str,
        previous_status: WorkflowStatus | None = None,
        next_status: WorkflowStatus | None = None, note: str | None = None,
    ) -> dict[str, Any]:
        audit = {
            "id": f"audit-{uuid.uuid4().hex}", "timestamp": TeacherWorkspaceStore._timestamp(),
            "actorId": actor.id, "actorName": actor.display_name, "action": action,
            "entityId": entity_id, "previousStatus": previous_status,
            "nextStatus": next_status, "note": note,
        }
        entries = state.setdefault("auditTrail", [])
        entries.append(audit)
        del entries[:-200]
        return audit

    def read(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT revision, payload FROM teacher_workspace WHERE singleton=1"
                ).fetchone()
                return copy.deepcopy(self._state(row))
        except sqlite3.Error as exc:
            raise RuntimeError("教师工作区数据库不可读") from exc

    def _mutate(
        self, expected_revision: int, mutation: Mutation
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT revision, payload FROM teacher_workspace WHERE singleton=1"
                ).fetchone()
                state = self._state(row)
                current = int(state["revision"])
                if expected_revision != current:
                    raise WorkspaceRevisionConflict("教学工作区已被其他教师更新，请刷新后重试")
                entity, audit = mutation(state)
                state["updatedAt"] = self._timestamp()
                state["revision"] = current + 1
                validated = self._validate(state)
                updated = connection.execute(
                    "UPDATE teacher_workspace SET revision=?, payload=?, updated_at=? "
                    "WHERE singleton=1 AND revision=?",
                    (validated["revision"], self._serialize(validated), self._timestamp(), current),
                )
                if updated.rowcount != 1:
                    raise WorkspaceRevisionConflict("教学工作区已被其他教师更新，请刷新后重试")
                connection.commit()
                return copy.deepcopy(entity), copy.deepcopy(audit), validated["revision"]
        except sqlite3.Error as exc:
            raise RuntimeError("教师工作区更新失败") from exc

    def update_alert(
        self, alert_id: str, status: AlertStatus, actor: TeacherActor,
        expected_revision: int, note: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            alert = next((item for item in state.get("alerts", []) if item.get("id") == alert_id), None)
            if alert is None:
                raise KeyError(alert_id)
            previous = alert.get("status")
            if previous not in {"new", "in_progress", "resolved"}:
                raise RuntimeError("教师关注项状态无效")
            alert["status"] = status
            audit = self._append_audit(
                state, actor, "alert_status_updated", alert_id, previous, status, note
            )
            return alert, audit
        return self._mutate(expected_revision, mutate)

    def update_intervention(
        self, intervention_id: str, status: str, actor: TeacherActor,
        expected_revision: int, note: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            intervention = next(
                (item for item in state.get("interventions", []) if item.get("id") == intervention_id),
                None,
            )
            if intervention is None:
                raise KeyError(intervention_id)
            previous = intervention.get("status")
            allowed = {("draft", "assigned"), ("assigned", "completed")}
            if (previous, status) not in allowed:
                raise ValueError("干预任务状态只能按草稿、已下发、已完成顺序推进")
            intervention["status"] = status
            timestamp_key = "assignedAt" if status == "assigned" else "completedAt"
            intervention[timestamp_key] = self._timestamp()
            if status == "completed":
                intervention["completionNote"] = note
            action = "intervention_assigned" if status == "assigned" else "intervention_completed"
            audit = self._append_audit(
                state, actor, action, intervention_id, previous, status, note
            )
            return intervention, audit
        return self._mutate(expected_revision, mutate)

    def create_intervention_draft(
        self, actor: TeacherActor, expected_revision: int,
        class_id: str | None = None, title: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            classes = {item.get("id"): item.get("name") for item in state.get("classes", [])}
            if class_id and class_id not in classes:
                raise ValueError("教学班不存在")
            candidates = [
                alert for alert in state.get("alerts", [])
                if alert.get("status") != "resolved"
                and (not class_id or alert.get("className") == classes[class_id])
            ]
            if not candidates:
                raise ValueError("当前范围没有可创建干预任务的关注项")
            draft = {
                "id": f"intervention-{uuid.uuid4().hex}",
                "title": title or f"{classes.get(class_id, '全部教学班')}实验干预任务",
                "classId": class_id or "all", "alertIds": [item["id"] for item in candidates],
                "status": "draft", "createdAt": self._timestamp(),
                "createdBy": {"id": actor.id, "name": actor.display_name},
            }
            state.setdefault("interventions", []).append(draft)
            audit = self._append_audit(
                state, actor, "intervention_draft_created", draft["id"],
                note=f"覆盖 {len(candidates)} 项关注线索",
            )
            return draft, audit
        return self._mutate(expected_revision, mutate)

    def import_live_workspace(
        self, workspace: dict[str, Any], actor: TeacherActor, expected_revision: int
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        incoming = self._validate(workspace)
        if incoming.get("dataSource") != "live":
            raise ValueError("导入工作区的 dataSource 必须为 live")

        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            preserved_revision = state["revision"]
            preserved_audit = state.get("auditTrail", [])[-199:]
            preserved_interventions = state.get("interventions", [])
            preserved_alert_statuses = {
                item.get("id"): item.get("status") for item in state.get("alerts", [])
            }
            state.clear()
            state.update(copy.deepcopy(incoming))
            state["revision"] = preserved_revision
            state["auditTrail"] = preserved_audit
            state["interventions"] = preserved_interventions
            for alert in state.get("alerts", []):
                previous_status = preserved_alert_statuses.get(alert.get("id"))
                if previous_status in {"new", "in_progress", "resolved"}:
                    alert["status"] = previous_status
            audit = self._append_audit(
                state, actor, "workspace_imported", "workspace",
                note="通过本地校验工具导入真实教学聚合数据",
            )
            return {"dataProfile": state["dataProfile"]}, audit

        return self._mutate(expected_revision, mutate)
