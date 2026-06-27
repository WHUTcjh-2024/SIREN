import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Load a minimal .env file without introducing a version-sensitive dependency."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    siren_env: str
    siren_host: str
    siren_port: int
    siren_cors_origins: tuple[str, ...]
    mimo_api_key: str
    mimo_base_url: str
    mimo_model: str
    max_upload_bytes: int

    @property
    def output_dir(self) -> Path:
        return ROOT_DIR / "output"

    @property
    def session_dir(self) -> Path:
        return ROOT_DIR / "data" / "experiment_sessions"


@lru_cache
def get_settings() -> Settings:
    _load_dotenv(ROOT_DIR / ".env")
    origins = tuple(
        value.strip() for value in os.getenv("SIREN_CORS_ORIGINS", "http://localhost:5173").split(",")
        if value.strip()
    )
    return Settings(
        siren_env=os.getenv("SIREN_ENV", "development"),
        siren_host=os.getenv("SIREN_HOST", "127.0.0.1"),
        siren_port=int(os.getenv("SIREN_PORT", "8000")),
        siren_cors_origins=origins,
        mimo_api_key=os.getenv("MIMO_API_KEY", ""),
        mimo_base_url=os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"),
        mimo_model=os.getenv("MIMO_MODEL", "mimo-v2.5"),
        max_upload_bytes=int(os.getenv("SIREN_MAX_UPLOAD_BYTES", str(16 * 1024 * 1024))),
    )
