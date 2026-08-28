import json
import threading
import uuid
from pathlib import Path
from typing import Any


HEAVY_KEYS = frozenset({"grayImage", "intensityProfile"})


class SessionStore:
    """Small local persistence adapter; replaceable by Redis/PostgreSQL."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._lock = threading.RLock()

    @staticmethod
    def _safe_sid(sid: str) -> str:
        try:
            parsed = uuid.UUID(sid)
        except (ValueError, AttributeError) as exc:
            raise ValueError("invalid session id") from exc
        if str(parsed) != sid.lower():
            raise ValueError("invalid session id")
        return str(parsed)

    @staticmethod
    def sanitize(state: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in state.items() if key not in HEAVY_KEYS}

    def _path(self, sid: str) -> Path:
        return self.directory / f"{self._safe_sid(sid)}.json"

    def read(self, sid: str) -> dict[str, Any]:
        path = self._path(sid)
        if not path.is_file():
            return {}
        try:
            return self.sanitize(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return {}

    def write(self, sid: str, state: dict[str, Any]) -> None:
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            target = self._path(sid)
            temporary = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
            try:
                temporary.write_text(
                    json.dumps(self.sanitize(state), ensure_ascii=False), encoding="utf-8"
                )
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)

    def delete(self, sid: str) -> None:
        with self._lock:
            self._path(sid).unlink(missing_ok=True)
