import threading
import time

from fastapi import HTTPException, Request

from backend.core.config import get_settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        with self._lock:
            events = [stamp for stamp in self._events.get(key, []) if now - stamp < window_seconds]
            if len(events) >= limit:
                raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")
            events.append(now)
            self._events[key] = events


_limiter = SlidingWindowLimiter()


def enforce_ai_rate_limit(request: Request) -> None:
    address = request.client.host if request.client else "unknown"
    _limiter.check(f"ai:{address}", get_settings().max_ai_requests_per_minute)
