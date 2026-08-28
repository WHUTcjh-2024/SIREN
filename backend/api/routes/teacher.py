import base64
import hashlib
import hmac
import json
import threading
import time
from hmac import compare_digest
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from backend.api.deps import get_teacher_workspace_store
from backend.core.config import Settings, get_settings
from backend.schemas.teacher import (
    AlertStatusWrite,
    AlertUpdateResponse,
    InterventionDraftResponse,
    InterventionDraftWrite,
    InterventionStatusWrite,
    TeacherActor,
    TeacherSessionWrite,
    TeacherWorkspaceResponse,
)
from backend.services.teacher_workspace import TeacherWorkspaceStore, WorkspaceRevisionConflict

router = APIRouter(tags=["teacher"])
SESSION_COOKIE = "siren_teacher_session"
SESSION_MAX_AGE = 8 * 60 * 60
_FAILED_LOGINS: dict[str, list[float]] = {}
_LOGIN_LOCK = threading.Lock()


def _session_key(settings: Settings) -> bytes:
    value = settings.teacher_access_code or "local-development-only"
    return hashlib.sha256(f"siren-teacher-session:{value}".encode()).digest()


def _encode_session(actor: TeacherActor, settings: Settings) -> str:
    payload = json.dumps(
        {"id": actor.id, "name": actor.display_name, "exp": int(time.time()) + SESSION_MAX_AGE},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(_session_key(settings), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _decode_session(token: str, settings: Settings) -> TeacherActor | None:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(
            _session_key(settings), encoded.encode(), hashlib.sha256
        ).hexdigest()
        if not compare_digest(supplied_signature, expected_signature):
            return None
        padding = "=" * (-len(encoded) % 4)
        payload: dict[str, Any] = json.loads(base64.urlsafe_b64decode(encoded + padding))
        if int(payload["exp"]) < int(time.time()):
            return None
        return TeacherActor(id=payload["id"], display_name=payload["name"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _login_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_login_rate_limit(request: Request) -> None:
    now = time.monotonic()
    key = _login_key(request)
    with _LOGIN_LOCK:
        recent = [stamp for stamp in _FAILED_LOGINS.get(key, []) if now - stamp < 300]
        _FAILED_LOGINS[key] = recent
        if len(recent) >= 5:
            raise HTTPException(status_code=429, detail="登录失败次数过多，请稍后重试")


def _record_failed_login(request: Request) -> None:
    with _LOGIN_LOCK:
        _FAILED_LOGINS.setdefault(_login_key(request), []).append(time.monotonic())


def _clear_failed_logins(request: Request) -> None:
    with _LOGIN_LOCK:
        _FAILED_LOGINS.pop(_login_key(request), None)


@router.post("/teacher/session")
def create_teacher_session(
    payload: TeacherSessionWrite,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict:
    _check_login_rate_limit(request)
    if settings.teacher_access_code and not compare_digest(
        payload.access_code, settings.teacher_access_code
    ):
        _record_failed_login(request)
        raise HTTPException(status_code=401, detail="教师访问码无效")
    _clear_failed_logins(request)
    actor = TeacherActor(id=settings.teacher_id[:64], display_name=settings.teacher_name[:80])
    response.set_cookie(
        SESSION_COOKIE,
        _encode_session(actor, settings),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path="/api/teacher",
    )
    return {"success": True, "actor": actor.model_dump()}


@router.delete("/teacher/session")
def delete_teacher_session(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/api/teacher", samesite="strict")
    return {"success": True}


def require_teacher_access(
    teacher_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    settings: Settings = Depends(get_settings),
) -> TeacherActor:
    """Verify the signed local-pilot session; production must later use campus SSO."""
    if not settings.teacher_access_code:
        return TeacherActor(id=settings.teacher_id[:64], display_name=settings.teacher_name[:80])
    actor = _decode_session(teacher_session or "", settings)
    if actor is None:
        raise HTTPException(status_code=401, detail="需要教师登录")
    return actor


def get_teacher_actor(
    actor: TeacherActor = Depends(require_teacher_access),
) -> TeacherActor:
    return actor


@router.get("/teacher/workspace", response_model=TeacherWorkspaceResponse)
def get_workspace(
    _: TeacherActor = Depends(require_teacher_access),
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


@router.patch("/teacher/interventions/{intervention_id}", response_model=InterventionDraftResponse)
def update_intervention(
    intervention_id: str,
    payload: InterventionStatusWrite,
    actor: TeacherActor = Depends(get_teacher_actor),
    store: TeacherWorkspaceStore = Depends(get_teacher_workspace_store),
) -> dict:
    try:
        intervention, audit, revision = store.update_intervention(
            intervention_id, payload.status, actor, payload.expected_revision, payload.note
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="干预任务不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspaceRevisionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "success": True,
        "data": {"intervention": intervention, "audit": audit, "revision": revision},
    }
