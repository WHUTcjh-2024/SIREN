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
    max_image_pixels: int
    max_concurrent_analyses: int
    max_saved_analysis_runs: int
    max_ai_requests_per_minute: int
    teacher_access_code: str
    teacher_id: str
    teacher_name: str

    @property
    def output_dir(self) -> Path:
        return ROOT_DIR / "output"

    @property
    def session_dir(self) -> Path:
        return ROOT_DIR / "data" / "experiment_sessions"

    @property
    def teacher_workspace_seed_file(self) -> Path:
        return ROOT_DIR / "data" / "teacher_workspace_seed.json"

    @property
    def teacher_workspace_file(self) -> Path:
        return ROOT_DIR / "data" / "teacher_workspace.json"

    @property
    def teacher_workspace_db_file(self) -> Path:
        return ROOT_DIR / "data" / "teacher_workspace.sqlite3"

    @property
    def is_production(self) -> bool:
        return self.siren_env.lower() == "production"

    def validate(self) -> None:
        if not 1024 <= self.max_upload_bytes <= 64 * 1024 * 1024:
            raise RuntimeError("SIREN_MAX_UPLOAD_BYTES 必须在 1 KiB 到 64 MiB 之间")
        if not 1_000_000 <= self.max_image_pixels <= 100_000_000:
            raise RuntimeError("SIREN_MAX_IMAGE_PIXELS 必须在 100 万到 1 亿之间")
        if not 1 <= self.max_concurrent_analyses <= 8:
            raise RuntimeError("SIREN_MAX_CONCURRENT_ANALYSES 必须在 1 到 8 之间")
        if not 1 <= self.max_saved_analysis_runs <= 1000:
            raise RuntimeError("SIREN_MAX_SAVED_ANALYSIS_RUNS 必须在 1 到 1000 之间")
        if not 1 <= self.max_ai_requests_per_minute <= 300:
            raise RuntimeError("SIREN_MAX_AI_REQUESTS_PER_MINUTE 必须在 1 到 300 之间")
        if "*" in self.siren_cors_origins:
            raise RuntimeError("SIREN_CORS_ORIGINS 不允许通配符")
        externally_bound = self.siren_host not in {"127.0.0.1", "localhost", "::1"}
        if (self.is_production or externally_bound) and len(self.teacher_access_code) < 16:
            raise RuntimeError("生产环境或非本机监听必须配置至少 16 字符的 TEACHER_ACCESS_CODE")


@lru_cache
def get_settings() -> Settings:
    _load_dotenv(ROOT_DIR / ".env")
    origins = tuple(
        value.strip() for value in os.getenv("SIREN_CORS_ORIGINS", "http://localhost:5173").split(",")
        if value.strip()
    )
    settings = Settings(
        siren_env=os.getenv("SIREN_ENV", "development"),
        siren_host=os.getenv("SIREN_HOST", "127.0.0.1"),
        siren_port=int(os.getenv("SIREN_PORT", "8000")),
        siren_cors_origins=origins,
        mimo_api_key=os.getenv("MIMO_API_KEY", ""),
        mimo_base_url=os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"),
        mimo_model=os.getenv("MIMO_MODEL", "mimo-v2.5"),
        max_upload_bytes=int(os.getenv("SIREN_MAX_UPLOAD_BYTES", str(16 * 1024 * 1024))),
        max_image_pixels=int(os.getenv("SIREN_MAX_IMAGE_PIXELS", "40000000")),
        max_concurrent_analyses=int(os.getenv("SIREN_MAX_CONCURRENT_ANALYSES", "1")),
        max_saved_analysis_runs=int(os.getenv("SIREN_MAX_SAVED_ANALYSIS_RUNS", "100")),
        max_ai_requests_per_minute=int(os.getenv("SIREN_MAX_AI_REQUESTS_PER_MINUTE", "30")),
        teacher_access_code=os.getenv("TEACHER_ACCESS_CODE", "").strip(),
        teacher_id=os.getenv("TEACHER_ID", "local-teacher").strip() or "local-teacher",
        teacher_name=os.getenv("TEACHER_NAME", "本地试点教师").strip() or "本地试点教师",
    )
    settings.validate()
    return settings
