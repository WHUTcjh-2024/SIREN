from functools import lru_cache

from backend.core.config import get_settings
from backend.services.agent import ExperimentAgent
from backend.services.session_store import SessionStore


@lru_cache
def get_session_store() -> SessionStore:
    return SessionStore(get_settings().session_dir)


@lru_cache
def get_agent() -> ExperimentAgent:
    return ExperimentAgent(get_settings())
