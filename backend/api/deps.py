from functools import lru_cache

from backend.core.config import get_settings
from backend.services.agent import ExperimentAgent
from backend.services.session_store import SessionStore
from backend.services.teacher_workspace import TeacherWorkspaceStore


@lru_cache
def get_session_store() -> SessionStore:
    return SessionStore(get_settings().session_dir)


@lru_cache
def get_agent() -> ExperimentAgent:
    return ExperimentAgent(get_settings())


@lru_cache
def get_teacher_workspace_store() -> TeacherWorkspaceStore:
    settings = get_settings()
    return TeacherWorkspaceStore(
        db_file=settings.teacher_workspace_db_file,
        seed_file=settings.teacher_workspace_seed_file,
        legacy_file=settings.teacher_workspace_file,
    )
