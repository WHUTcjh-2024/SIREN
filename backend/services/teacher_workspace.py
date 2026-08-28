import copy
import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.schemas.teacher import AlertStatus, TeacherActor


class WorkspaceRevisionConflict(RuntimeError):
    """Raised when a write is based on a stale teacher-workspace revision."""


class TeacherWorkspaceStore:
    """Small file-backed workspace store used by the local teaching pilot.

    The seed file is immutable demo input. Runtime changes are written to a
    separate file so teacher actions remain durable without altering fixtures.
    Replace this adapter with a database repository for multi-tenant deployment.
    """

    def __init__(self, workspace_file: Path, seed_file: Path):
        self.workspace_file = workspace_file
        self.seed_file = seed_file
        self._lock = threading.RLock()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("教师工作区数据不可读取") from exc
        if not isinstance(value, dict):
            raise RuntimeError("教师工作区数据格式无效")
        return value

    def _load_state(self) -> dict[str, Any]:
        if self.workspace_file.is_file():
            state = self._read_json(self.workspace_file)
            if "dataProfile" in state:
                return state
            return self._migrate_legacy_state(state)
        if not self.seed_file.is_file():
            raise RuntimeError("教师工作区种子数据不存在")
        state = self._read_json(self.seed_file)
        self._write_state(state)
        return state

    def _migrate_legacy_state(self, previous_state: dict[str, Any]) -> dict[str, Any]:
        """Refresh an old local workspace while preserving teacher-made decisions.

        The data profile is a required part of the data-driven demonstration. Old
        workspace snapshots do not contain it, so they are upgraded from the
        current seed instead of failing the API response validation.
        """

        if not self.seed_file.is_file():
            raise RuntimeError("教师工作区种子数据不存在")
        state = self._read_json(self.seed_file)
        previous_statuses = {
            item.get("id"): item.get("status")
            for item in previous_state.get("alerts", [])
            if item.get("id") and item.get("status") in {"new", "in_progress", "resolved"}
        }
        for alert in state.get("alerts", []):
            if alert.get("id") in previous_statuses:
                alert["status"] = previous_statuses[alert["id"]]
        state["interventions"] = previous_state.get("interventions", [])
        state["auditTrail"] = previous_state.get("auditTrail", [])[-200:]
        state["revision"] = max(
            int(state.get("revision", 0)),
            int(previous_state.get("revision", 0)),
        )
        self._write_state(state)
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        self.workspace_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.workspace_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.workspace_file)

    @staticmethod
    def _append_audit(
        state: dict[str, Any],
        actor: TeacherActor,
        action: str,
        entity_id: str,
        previous_status: AlertStatus | None = None,
        next_status: AlertStatus | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        audit = {
            "id": f"audit-{uuid.uuid4().hex}",
            "timestamp": TeacherWorkspaceStore._timestamp(),
            "actorId": actor.id,
            "actorName": actor.display_name,
            "action": action,
            "entityId": entity_id,
            "previousStatus": previous_status,
            "nextStatus": next_status,
            "note": note,
        }
        entries = state.setdefault("auditTrail", [])
        entries.append(audit)
        del entries[:-200]
        return audit

    def read(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._load_state())

    def update_alert(
        self,
        alert_id: str,
        status: AlertStatus,
        actor: TeacherActor,
        expected_revision: int,
        note: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        with self._lock:
            state = self._load_state()
            current_revision = int(state.get("revision", 0))
            if expected_revision != current_revision:
                raise WorkspaceRevisionConflict("教学工作区已被其他教师更新，请刷新后重试")
            alert = next((item for item in state.get("alerts", []) if item.get("id") == alert_id), None)
            if alert is None:
                raise KeyError(alert_id)

            previous_status = alert.get("status")
            if previous_status not in {"new", "in_progress", "resolved"}:
                raise RuntimeError("教师关注项状态无效")
            alert["status"] = status
            state["updatedAt"] = self._timestamp()
            state["revision"] = current_revision + 1
            audit = self._append_audit(
                state,
                actor,
                "alert_status_updated",
                alert_id,
                previous_status=previous_status,
                next_status=status,
                note=note,
            )
            self._write_state(state)
            return copy.deepcopy(alert), audit, state["revision"]

    def create_intervention_draft(
        self,
        actor: TeacherActor,
        expected_revision: int,
        class_id: str | None = None,
        title: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        with self._lock:
            state = self._load_state()
            current_revision = int(state.get("revision", 0))
            if expected_revision != current_revision:
                raise WorkspaceRevisionConflict("教学工作区已被其他教师更新，请刷新后重试")
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
                "classId": class_id or "all",
                "alertIds": [item["id"] for item in candidates],
                "status": "draft",
                "createdAt": self._timestamp(),
                "createdBy": {"id": actor.id, "name": actor.display_name},
            }
            state.setdefault("interventions", []).append(draft)
            state["updatedAt"] = draft["createdAt"]
            state["revision"] = current_revision + 1
            audit = self._append_audit(
                state,
                actor,
                "intervention_draft_created",
                draft["id"],
                note=f"覆盖 {len(candidates)} 项关注线索",
            )
            self._write_state(state)
            return copy.deepcopy(draft), audit, state["revision"]
