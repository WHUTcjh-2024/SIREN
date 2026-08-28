import uuid

from fastapi import APIRouter, Cookie, Depends, Response

from backend.api.deps import get_session_store
from backend.core.config import Settings, get_settings
from backend.schemas.experiment import CalculationRequest, ExperimentStateWrite, FitRequest
from backend.services.calculation import calculate_surface_tension, fit_surface_tension
from backend.services.session_store import SessionStore

router = APIRouter(tags=["experiments"])


def _canonical_session_id(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    try:
        parsed = uuid.UUID(raw_value)
    except (ValueError, AttributeError):
        return None
    canonical = str(parsed)
    return canonical if raw_value.lower() == canonical else None


@router.get("/experiment-state")
def get_state(exp_sid: str | None = Cookie(default=None),
              store: SessionStore = Depends(get_session_store)) -> dict:
    session_id = _canonical_session_id(exp_sid)
    return {"success": True, "data": store.read(session_id) if session_id else {}}


@router.post("/experiment-state")
def save_state(payload: ExperimentStateWrite, response: Response,
               exp_sid: str | None = Cookie(default=None),
               settings: Settings = Depends(get_settings),
               store: SessionStore = Depends(get_session_store)) -> dict:
    session_id = _canonical_session_id(exp_sid)
    if session_id is None:
        generated_session_id = str(uuid.uuid4())
        store.write(generated_session_id, payload.state)
        response.set_cookie(
            "exp_sid", generated_session_id, max_age=86400 * 30, httponly=True,
            secure=settings.is_production, samesite="strict", path="/api",
        )
    else:
        store.write(session_id, payload.state)
    return {"success": True}


@router.post("/experiment-reset")
def reset_state(response: Response, exp_sid: str | None = Cookie(default=None),
                store: SessionStore = Depends(get_session_store)) -> dict:
    session_id = _canonical_session_id(exp_sid)
    if session_id:
        store.delete(session_id)
    response.delete_cookie("exp_sid", path="/api", samesite="strict")
    return {"success": True, "message": "实验缓存已清空"}


@router.post("/calculate")
def calculate(payload: CalculationRequest) -> dict:
    return {"success": True, "data": calculate_surface_tension(payload)}


@router.post("/fit")
def fit(payload: FitRequest) -> dict:
    return {"success": True, "data": fit_surface_tension(payload)}
