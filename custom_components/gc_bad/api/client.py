"""HTTP API client for GoCardless endpoints."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import API_BASE_URL
from ..storage import IntegrationStorage
from .auth import GCBadAuthError, TokenManager
from .rate_limits import DailyRateLimiter

_LOGGER = logging.getLogger(__name__)


class GCBadApiError(Exception):
    """Base API error."""


class GCBadCannotConnectError(GCBadApiError):
    """Raised when transport to API fails."""


class GCBadRateLimitError(GCBadApiError):
    """Raised when local rate limiter blocks requests."""


class GCBadResponseError(GCBadApiError):
    """Raised when API returns invalid payload."""


class GoCardlessApiClient:
    """GoCardless Bank Account Data client."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: IntegrationStorage,
        secret_id: str,
        secret_key: str,
    ) -> None:
        """Initialize API client."""
        self._session = async_get_clientsession(hass)
        self._token_manager = TokenManager(storage, self._session, secret_id, secret_key)
        self._rate_limiter = DailyRateLimiter(storage)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        rate_limit_key: str | None = None,
        max_per_day: int | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        """Perform authenticated request with optional rate limiting."""
        if rate_limit_key and max_per_day is not None:
            allowed = await self._rate_limiter.allow(rate_limit_key, max_per_day)
            if not allowed:
                raise GCBadRateLimitError(f"Rate limit exceeded for {rate_limit_key}")

        try:
            access_token = await self._token_manager.get_access_token()
        except GCBadAuthError as err:
            raise GCBadApiError(str(err)) from err

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = f"{API_BASE_URL}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json_payload,
            ) as response:
                lowered_headers = {
                    key.lower(): value for key, value in response.headers.items()
                }
                if rate_limit_key:
                    await self._rate_limiter.update_from_headers(
                        rate_limit_key,
                        lowered_headers,
                    )
                if response.status == 401:
                    await self._token_manager.invalidate()
                    raise GCBadAuthError("Authentication failed")
                response.raise_for_status()
                if response.status == 204:
                    return None
                return await response.json()
        except GCBadAuthError as err:
            raise GCBadApiError(str(err)) from err
        except aiohttp.ClientResponseError as err:
            raise GCBadApiError(f"API response error {err.status}: {err.message}") from err
        except aiohttp.ClientError as err:
            raise GCBadCannotConnectError(f"Connection failed: {err}") from err

    async def validate_api_key(self) -> bool:
        """Validate credentials by calling requisitions endpoint."""
        try:
            await self.get_requisitions()
            return True
        except GCBadApiError:
            return False

    async def get_requisitions(self) -> list[dict[str, Any]]:
        """List all requisitions."""
        payload = await self._request("GET", "/api/v2/requisitions/")
        if not isinstance(payload, dict):
            raise GCBadResponseError("Requisitions response must be an object")
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise GCBadResponseError("Requisitions results must be a list")
        return [item for item in results if isinstance(item, dict)]

    async def get_requisition(self, requisition_id: str) -> dict[str, Any]:
        """Fetch a single requisition."""
        payload = await self._request("GET", f"/api/v2/requisitions/{requisition_id}/")
        if not isinstance(payload, dict):
            raise GCBadResponseError("Requisition payload must be an object")
        return payload

    async def get_account_details(
        self,
        account_id: str,
        max_per_day: int,
    ) -> dict[str, Any]:
        """Fetch account details."""
        payload = await self._request(
            "GET",
            f"/api/v2/accounts/{account_id}/details/",
            rate_limit_key=f"details_{account_id}",
            max_per_day=max_per_day,
        )
        if not isinstance(payload, dict):
            raise GCBadResponseError("Account details payload must be an object")
        return payload

    async def get_account_balances(
        self,
        account_id: str,
        max_per_day: int,
    ) -> dict[str, Any]:
        """Fetch account balances."""
        payload = await self._request(
            "GET",
            f"/api/v2/accounts/{account_id}/balances/",
            rate_limit_key=f"balances_{account_id}",
            max_per_day=max_per_day,
        )
        if not isinstance(payload, dict):
            raise GCBadResponseError("Account balances payload must be an object")
        return payload

    async def get_account_transactions(
        self,
        account_id: str,
        max_per_day: int,
    ) -> dict[str, Any]:
        """Fetch account transactions."""
        payload = await self._request(
            "GET",
            f"/api/v2/accounts/{account_id}/transactions/",
            rate_limit_key=f"transactions_{account_id}",
            max_per_day=max_per_day,
        )
        if not isinstance(payload, dict):
            raise GCBadResponseError("Account transactions payload must be an object")
        return payload

    async def get_institutions(self, country: str) -> list[dict[str, Any]]:
        """List institutions by country code."""
        payload = await self._request(
            "GET",
            f"/api/v2/institutions/?country={country}",
        )
        if not isinstance(payload, list):
            raise GCBadResponseError("Institutions payload must be a list")
        return [item for item in payload if isinstance(item, dict)]

    async def get_institution(self, institution_id: str) -> dict[str, Any]:
        """Fetch institution details."""
        payload = await self._request("GET", f"/api/v2/institutions/{institution_id}/")
        if not isinstance(payload, dict):
            raise GCBadResponseError("Institution payload must be an object")
        return payload

    async def create_requisition(
        self,
        institution_id: str,
        redirect_url: str,
        reference: str,
    ) -> dict[str, Any]:
        """Create a new requisition."""
        payload = await self._request(
            "POST",
            "/api/v2/requisitions/",
            json_payload={
                "institution_id": institution_id,
                "redirect": redirect_url,
                "reference": reference,
            },
        )
        if not isinstance(payload, dict):
            raise GCBadResponseError("Requisition create payload must be an object")
        return payload

    async def delete_requisition(self, requisition_id: str) -> None:
        """Delete requisition."""
        await self._request("DELETE", f"/api/v2/requisitions/{requisition_id}/")
