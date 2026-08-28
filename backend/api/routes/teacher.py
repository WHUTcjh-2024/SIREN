import re
from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from backend.api.deps import get_teacher_workspace_store
from backend.core.config import Settings, get_settings
from backend.schemas.teacher import (
    AlertStatusWrite,
    AlertUpdateResponse,
    InterventionDraftResponse,
    InterventionDraftWrite,
    TeacherActor,
    TeacherWorkspaceResponse,
)
from backend.services.teacher_workspace import TeacherWorkspaceStore, WorkspaceRevisionConflict

router = APIRouter(tags=["teacher"])


def require_teacher_access(
    x_teacher_access_code: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """Optional access-code gate for a LAN pilot until campus SSO is connected."""
    if not settings.teacher_access_code:
        return
    if not x_teacher_access_code or not compare_digest(
        x_teacher_access_code, settings.teacher_access_code
    ):
        raise HTTPException(status_code=401, detail="需要教师访问码")


def get_teacher_actor(
    x_teacher_id: Annotated[str | None, Header()] = None,
    x_teacher_name: Annotated[str | None, Header()] = None,
    _: None = Depends(require_teacher_access),
) -> TeacherActor:
    """Local-pilot actor resolver.

    A deployment must replace this dependency with campus SSO/OIDC and enforce
    organization, course and class permissions at the repository boundary.
    """
    raw_id = x_teacher_id or "local-teacher"
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", raw_id)[:64]
    if not safe_id:
        raise HTTPException(status_code=400, detail="教师身份标识无效")
    raw_name = (x_teacher_name or "本地试点教师").strip()
    return TeacherActor(id=safe_id, display_name=raw_name[:80] or "本地试点教师")


@router.get("/teacher/workspace", response_model=TeacherWorkspaceResponse)
def get_workspace(
    _: None = Depends(require_teacher_access),
    store: TeacherWorkspaceStore = Depends(get_teacher_workspace_store),
) -> dict:
    try:
        workspace = store.read()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "success": True,
        "data": workspace,
        "source": workspace.get("dataSource", "live"),
        "revision": workspace.get("revision", 0),
    }


@router.patch("/teacher/alerts/{alert_id}", response_model=AlertUpdateResponse)
def update_alert(
    alert_id: str,
    payload: AlertStatusWrite,
    actor: TeacherActor = Depends(get_teacher_actor),
    store: TeacherWorkspaceStore = Depends(get_teacher_workspace_store),
) -> dict:
    try:
        alert, audit, revision = store.update_alert(
            alert_id,
            payload.status,
            actor,
            payload.expected_revision,
            payload.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="教师关注项不存在") from exc
    except WorkspaceRevisionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "data": {"alert": alert, "audit": audit, "revision": revision}}


@router.post("/teacher/interventions/drafts", response_model=InterventionDraftResponse)
def create_intervention_draft(
    payload: InterventionDraftWrite,
    actor: TeacherActor = Depends(get_teacher_actor),
    store: TeacherWorkspaceStore = Depends(get_teacher_workspace_store),
) -> dict:
    try:
        draft, audit, revision = store.create_intervention_draft(
            actor,
            payload.expected_revision,
            payload.class_id,
            payload.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspaceRevisionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "success": True,
        "data": {"intervention": draft, "audit": audit, "revision": revision},
    }
