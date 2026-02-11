"""Storage boundaries for API state and coordinator snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION
from .models import IntegrationSnapshot


@dataclass(slots=True)
class ApiState:
    """Token and rate limit state persisted between restarts."""

    access_token: str | None
    refresh_token: str | None
    access_expires_at: str | None
    refresh_expires_at: str | None
    rate_limits: dict[str, dict[str, Any]]

    @classmethod
    def empty(cls) -> "ApiState":
        """Return an empty API state."""
        return cls(
            access_token=None,
            refresh_token=None,
            access_expires_at=None,
            refresh_expires_at=None,
            rate_limits={},
        )


class IntegrationStorage:
    """Storage helper that isolates persistence schema details."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize stores for a single config entry."""
        self._api_store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}_api_state_{entry_id}",
        )
        self._snapshot_store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}_snapshot_{entry_id}",
        )

    async def load_api_state(self) -> ApiState:
        """Load API state from storage."""
        data = await self._api_store.async_load()
        if not data:
            return ApiState.empty()

        return ApiState(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            access_expires_at=data.get("access_expires_at"),
            refresh_expires_at=data.get("refresh_expires_at"),
            rate_limits=dict(data.get("rate_limits", {})),
        )

    async def save_api_state(self, state: ApiState) -> None:
        """Persist API state."""
        await self._api_store.async_save(
            {
                "access_token": state.access_token,
                "refresh_token": state.refresh_token,
                "access_expires_at": state.access_expires_at,
                "refresh_expires_at": state.refresh_expires_at,
                "rate_limits": state.rate_limits,
            }
        )

    async def clear_api_state(self) -> None:
        """Remove persisted API state."""
        await self._api_store.async_remove()

    async def load_snapshot(self) -> IntegrationSnapshot | None:
        """Load cached integration snapshot."""
        data = await self._snapshot_store.async_load()
        if not data:
            return None
        return IntegrationSnapshot.from_dict(data)

    async def save_snapshot(
        self,
        snapshot: IntegrationSnapshot,
        last_successful_refresh: datetime,
    ) -> None:
        """Persist integration snapshot."""
        payload = snapshot.as_dict()
        payload["last_successful_refresh"] = last_successful_refresh.isoformat()
        await self._snapshot_store.async_save(payload)
