"""Configuration-aware production entry point."""

import uvicorn

from backend.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.siren_host,
        port=settings.siren_port,
        proxy_headers=settings.is_production,
        forwarded_allow_ips="127.0.0.1" if settings.is_production else None,
    )


if __name__ == "__main__":
    main()
