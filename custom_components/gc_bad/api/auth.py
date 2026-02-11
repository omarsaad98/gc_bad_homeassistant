"""Authentication/token management for GoCardless API."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util

from ..const import API_BASE_URL
from ..storage import ApiState, IntegrationStorage

_LOGGER = logging.getLogger(__name__)


class GCBadAuthError(Exception):
    """Raised when authentication fails."""


class TokenManager:
    """Manages access/refresh token lifecycle with persistence."""

    def __init__(
        self,
        storage: IntegrationStorage,
        session: aiohttp.ClientSession,
        secret_id: str,
        secret_key: str,
    ) -> None:
        """Initialize token manager."""
        self._storage = storage
        self._session = session
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._loaded = False
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._access_expires_at: str | None = None
        self._refresh_expires_at: str | None = None

    async def _load(self) -> None:
        """Load token state once from storage."""
        if self._loaded:
            return
        state = await self._storage.load_api_state()
        self._access_token = state.access_token
        self._refresh_token = state.refresh_token
        self._access_expires_at = state.access_expires_at
        self._refresh_expires_at = state.refresh_expires_at
        self._loaded = True

    async def _save(self) -> None:
        """Persist token state while preserving rate limits."""
        current = await self._storage.load_api_state()
        await self._storage.save_api_state(
            ApiState(
                access_token=self._access_token,
                refresh_token=self._refresh_token,
                access_expires_at=self._access_expires_at,
                refresh_expires_at=self._refresh_expires_at,
                rate_limits=current.rate_limits,
            )
        )

    def _is_valid(self, expires_at: str | None) -> bool:
        """Check whether a timestamp is still valid."""
        if not expires_at:
            return False
        parsed = dt_util.parse_datetime(expires_at)
        if parsed is None:
            return False
        return dt_util.utcnow() < parsed

    async def get_access_token(self) -> str:
        """Return a valid access token."""
        await self._load()
        if self._access_token and self._is_valid(self._access_expires_at):
            return self._access_token

        if self._refresh_token and self._is_valid(self._refresh_expires_at):
            try:
                await self._refresh_access_token()
                if self._access_token:
                    return self._access_token
            except GCBadAuthError:
                _LOGGER.debug("Refresh token path failed, requesting new token")

        await self._request_new_token()
        if self._access_token is None:
            raise GCBadAuthError("No access token received")
        return self._access_token

    async def invalidate(self) -> None:
        """Invalidate cached tokens."""
        self._access_token = None
        self._access_expires_at = None
        await self._save()

    async def _request_new_token(self) -> None:
        """Request new access/refresh token pair."""
        endpoint = f"{API_BASE_URL}/api/v2/token/new/"
        payload = {"secret_id": self._secret_id, "secret_key": self._secret_key}
        try:
            async with self._session.post(endpoint, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise GCBadAuthError(f"Failed to request token: {err}") from err

        self._apply_token_payload(data)
        await self._save()

    async def _refresh_access_token(self) -> None:
        """Refresh access token with refresh token."""
        endpoint = f"{API_BASE_URL}/api/v2/token/refresh/"
        payload = {"refresh": self._refresh_token}
        try:
            async with self._session.post(endpoint, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise GCBadAuthError(f"Failed to refresh token: {err}") from err

        access = data.get("access")
        if not access:
            raise GCBadAuthError("Refresh response missing access token")

        access_expires = int(data.get("access_expires", 86400))
        self._access_token = access
        self._access_expires_at = (
            dt_util.utcnow() + timedelta(seconds=max(access_expires - 60, 60))
        ).isoformat()
        await self._save()

    def _apply_token_payload(self, data: dict[str, Any]) -> None:
        """Update in-memory tokens from API response."""
        access = data.get("access")
        if not access:
            raise GCBadAuthError("Token response missing access token")

        refresh = data.get("refresh")
        access_expires = int(data.get("access_expires", 86400))
        refresh_expires = int(data.get("refresh_expires", 2592000))

        self._access_token = access
        self._refresh_token = refresh
        self._access_expires_at = (
            dt_util.utcnow() + timedelta(seconds=max(access_expires - 60, 60))
        ).isoformat()
        self._refresh_expires_at = (
            dt_util.utcnow() + timedelta(seconds=refresh_expires)
        ).isoformat()
