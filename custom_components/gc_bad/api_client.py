"""API client for GoCardless Bank Account Data API."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class GoCardlessAPIClient:
    """GoCardless API client with rate limit management."""

    def __init__(self, hass: HomeAssistant, api_secret: str) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._api_secret = api_secret
        self._session = async_get_clientsession(hass)
        self._base_url = API_BASE_URL
        
        # Rate limit tracking per endpoint
        self._rate_limits: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self._api_secret}",
            "Content-Type": "application/json",
        }

    async def _check_rate_limit(self, endpoint_key: str, max_per_day: int) -> bool:
        """Check if we can make a request based on rate limits."""
        async with self._lock:
            now = datetime.now()
            if endpoint_key not in self._rate_limits:
                self._rate_limits[endpoint_key] = {
                    "count": 0,
                    "reset_time": now + timedelta(days=1),
                }
            
            limit_info = self._rate_limits[endpoint_key]
            
            # Reset if day has passed
            if now >= limit_info["reset_time"]:
                limit_info["count"] = 0
                limit_info["reset_time"] = now + timedelta(days=1)
            
            # Check if we can make the request
            if limit_info["count"] >= max_per_day:
                _LOGGER.warning(
                    "Rate limit reached for %s. Reset at %s",
                    endpoint_key,
                    limit_info["reset_time"],
                )
                return False
            
            limit_info["count"] += 1
            return True

    async def _request(
        self,
        method: str,
        endpoint: str,
        rate_limit_key: str | None = None,
        max_per_day: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request with rate limit checking."""
        if rate_limit_key and max_per_day:
            if not await self._check_rate_limit(rate_limit_key, max_per_day):
                raise Exception(f"Rate limit exceeded for {rate_limit_key}")
        
        url = f"{self._base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                # Check rate limit headers
                if "X-RateLimit-Remaining" in response.headers:
                    remaining = response.headers["X-RateLimit-Remaining"]
                    _LOGGER.debug("Rate limit remaining: %s", remaining)
                
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as err:
            if err.status == 429:
                _LOGGER.error("Rate limit exceeded: %s", err)
            elif err.status == 401:
                _LOGGER.error("Authentication failed: %s", err)
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("API request failed: %s", err)
            raise

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request."""
        try:
            # Test with a simple requisitions list call
            await self._request("GET", "/api/v2/requisitions/")
            return True
        except Exception as err:
            _LOGGER.error("API key validation failed: %s", err)
            return False

    async def get_requisitions(self) -> list[dict[str, Any]]:
        """Get all requisitions."""
        try:
            response = await self._request("GET", "/api/v2/requisitions/")
            return response.get("results", [])
        except Exception as err:
            _LOGGER.error("Failed to get requisitions: %s", err)
            return []

    async def get_requisition(self, requisition_id: str) -> dict[str, Any] | None:
        """Get a specific requisition."""
        try:
            return await self._request("GET", f"/api/v2/requisitions/{requisition_id}/")
        except Exception as err:
            _LOGGER.error("Failed to get requisition %s: %s", requisition_id, err)
            return None

    async def get_account_details(
        self, account_id: str, max_per_day: int = 2
    ) -> dict[str, Any] | None:
        """Get account details with rate limiting."""
        try:
            return await self._request(
                "GET",
                f"/api/v2/accounts/{account_id}/details/",
                rate_limit_key=f"details_{account_id}",
                max_per_day=max_per_day,
            )
        except Exception as err:
            _LOGGER.error("Failed to get account details for %s: %s", account_id, err)
            return None

    async def get_account_balances(
        self, account_id: str, max_per_day: int = 2
    ) -> dict[str, Any] | None:
        """Get account balances with rate limiting."""
        try:
            return await self._request(
                "GET",
                f"/api/v2/accounts/{account_id}/balances/",
                rate_limit_key=f"balances_{account_id}",
                max_per_day=max_per_day,
            )
        except Exception as err:
            _LOGGER.error("Failed to get account balances for %s: %s", account_id, err)
            return None

    async def get_account_transactions(
        self, account_id: str, max_per_day: int = 4
    ) -> dict[str, Any] | None:
        """Get account transactions with rate limiting."""
        try:
            return await self._request(
                "GET",
                f"/api/v2/accounts/{account_id}/transactions/",
                rate_limit_key=f"transactions_{account_id}",
                max_per_day=max_per_day,
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to get account transactions for %s: %s", account_id, err
            )
            return None

    async def get_institutions(self, country: str) -> list[dict[str, Any]]:
        """Get list of institutions for a country."""
        try:
            response = await self._request(
                "GET", f"/api/v2/institutions/?country={country}"
            )
            return response if isinstance(response, list) else []
        except Exception as err:
            _LOGGER.error("Failed to get institutions for %s: %s", country, err)
            return []

    async def create_requisition(
        self,
        institution_id: str,
        redirect_url: str,
        reference: str | None = None,
    ) -> dict[str, Any] | None:
        """Create a new requisition (bank connection)."""
        try:
            data = {
                "institution_id": institution_id,
                "redirect": redirect_url,
            }
            if reference:
                data["reference"] = reference
            
            return await self._request("POST", "/api/v2/requisitions/", json=data)
        except Exception as err:
            _LOGGER.error("Failed to create requisition: %s", err)
            return None

    async def delete_requisition(self, requisition_id: str) -> bool:
        """Delete a requisition."""
        try:
            await self._request("DELETE", f"/api/v2/requisitions/{requisition_id}/")
            return True
        except Exception as err:
            _LOGGER.error("Failed to delete requisition %s: %s", requisition_id, err)
            return False

