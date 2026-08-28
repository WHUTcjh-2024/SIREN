import uuid

from fastapi import APIRouter, Cookie, Depends, Response

from backend.api.deps import get_session_store
from backend.core.config import Settings, get_settings
from backend.schemas.experiment import CalculationRequest, ExperimentStateWrite, FitRequest
from backend.services.calculation import calculate_surface_tension, fit_surface_tension
from backend.services.session_store import SessionStore

router = APIRouter(tags=["experiments"])


@router.get("/experiment-state")
def get_state(exp_sid: str | None = Cookie(default=None),
              store: SessionStore = Depends(get_session_store)) -> dict:
    return {"success": True, "data": store.read(exp_sid) if exp_sid else {}}


@router.post("/experiment-state")
def save_state(payload: ExperimentStateWrite, response: Response,
               exp_sid: str | None = Cookie(default=None),
               settings: Settings = Depends(get_settings),
               store: SessionStore = Depends(get_session_store)) -> dict:
    session_id = exp_sid or str(uuid.uuid4())
    store.write(session_id, payload.state)
    response.set_cookie(
        "exp_sid", session_id, max_age=86400 * 30, httponly=True,
        secure=settings.is_production, samesite="strict", path="/api",
    )
    return {"success": True}


@router.post("/experiment-reset")
def reset_state(response: Response, exp_sid: str | None = Cookie(default=None),
                store: SessionStore = Depends(get_session_store)) -> dict:
    if exp_sid:
        store.delete(exp_sid)
    response.delete_cookie("exp_sid", path="/api", samesite="strict")
    return {"success": True, "message": "实验缓存已清空"}


@router.post("/calculate")
def calculate(payload: CalculationRequest) -> dict:
    return {"success": True, "data": calculate_surface_tension(payload)}


@router.post("/fit")
def fit(payload: FitRequest) -> dict:
    return {"success": True, "data": fit_surface_tension(payload)}
