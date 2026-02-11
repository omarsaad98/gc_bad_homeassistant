"""Rate limit policy and persistence helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.util import dt as dt_util

from ..storage import ApiState, IntegrationStorage

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RateLimitCounter:
    """In-memory counter for one scoped endpoint."""

    count: int
    reset_at: str
    api_limit: int | None

    @classmethod
    def new_window(cls) -> "RateLimitCounter":
        """Create a fresh 24 hour window counter."""
        reset_at = (dt_util.utcnow() + timedelta(days=1)).isoformat()
        return cls(count=0, reset_at=reset_at, api_limit=None)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RateLimitCounter":
        """Deserialize counter from persisted state."""
        return cls(
            count=int(data.get("count", 0)),
            reset_at=str(data.get("reset_at")),
            api_limit=data.get("api_limit"),
        )

    def as_dict(self) -> dict[str, Any]:
        """Serialize counter to storage dict."""
        return {
            "count": self.count,
            "reset_at": self.reset_at,
            "api_limit": self.api_limit,
        }


class DailyRateLimiter:
    """Per-endpoint daily limiter with persisted counters."""

    def __init__(self, storage: IntegrationStorage) -> None:
        """Initialize limiter."""
        self._storage = storage
        self._counters: dict[str, RateLimitCounter] = {}
        self._loaded = False

    async def async_load(self) -> None:
        """Load counters from persisted API state."""
        if self._loaded:
            return
        state = await self._storage.load_api_state()
        for key, raw in state.rate_limits.items():
            if isinstance(raw, dict):
                self._counters[key] = RateLimitCounter.from_dict(raw)
        self._loaded = True

    async def _persist(self) -> None:
        """Persist counters while preserving token fields."""
        state = await self._storage.load_api_state()
        new_state = ApiState(
            access_token=state.access_token,
            refresh_token=state.refresh_token,
            access_expires_at=state.access_expires_at,
            refresh_expires_at=state.refresh_expires_at,
            rate_limits={key: counter.as_dict() for key, counter in self._counters.items()},
        )
        await self._storage.save_api_state(new_state)

    async def allow(self, key: str, default_limit: int) -> bool:
        """Return True when a request is still allowed."""
        await self.async_load()
        counter = self._counters.get(key)
        if counter is None:
            counter = RateLimitCounter.new_window()
            self._counters[key] = counter

        now = dt_util.utcnow()
        reset_at = dt_util.parse_datetime(counter.reset_at)
        if reset_at is None or now >= reset_at:
            counter = RateLimitCounter.new_window()
            self._counters[key] = counter

        effective_limit = counter.api_limit or default_limit
        if counter.count >= effective_limit:
            _LOGGER.warning(
                "Rate limit reached for %s (%s/%s)",
                key,
                counter.count,
                effective_limit,
            )
            return False

        counter.count += 1
        await self._persist()
        return True

    async def update_from_headers(self, key: str, headers: dict[str, str]) -> None:
        """Update API-based limit from response headers."""
        await self.async_load()
        counter = self._counters.get(key)
        if counter is None:
            return

        raw_limit = headers.get("x-ratelimit-account-success-limit")
        if raw_limit is None:
            return

        try:
            api_limit = int(raw_limit)
        except (TypeError, ValueError):
            return

        buffered_limit = max(1, int(api_limit * 0.75))
        if counter.api_limit != buffered_limit:
            counter.api_limit = buffered_limit
            await self._persist()
