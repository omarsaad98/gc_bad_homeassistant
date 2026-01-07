"""API client for GoCardless Bank Account Data API."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import API_BASE_URL, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class GoCardlessAPIClient:
    """GoCardless API client with rate limit management."""

    def __init__(self, hass: HomeAssistant, secret_id: str, secret_key: str) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._session = async_get_clientsession(hass)
        self._base_url = API_BASE_URL
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires: datetime | None = None
        self._refresh_expires: datetime | None = None
        
        # Rate limit tracking per endpoint
        self._rate_limits: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        # Storage for persistence
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{secret_id[:8]}",
        )
        self._storage_loaded = False

    async def _load_storage(self) -> None:
        """Load tokens and rate limits from storage."""
        if self._storage_loaded:
            return
        
        data = await self._store.async_load()
        if data:
            # Load tokens
            tokens = data.get("tokens", {})
            if tokens:
                self._access_token = tokens.get("access_token")
                self._refresh_token = tokens.get("refresh_token")
                
                # Parse expiry times
                if tokens.get("access_expires"):
                    self._token_expires = datetime.fromisoformat(tokens["access_expires"])
                if tokens.get("refresh_expires"):
                    self._refresh_expires = datetime.fromisoformat(tokens["refresh_expires"])
                
                _LOGGER.info("Loaded tokens from storage (expires: %s)", self._token_expires)
            
            # Load rate limits
            rate_limits = data.get("rate_limits", {})
            for key, limit_data in rate_limits.items():
                if limit_data.get("reset_time"):
                    limit_data["reset_time"] = datetime.fromisoformat(limit_data["reset_time"])
            self._rate_limits = rate_limits
            
            if rate_limits:
                _LOGGER.info("Loaded %d rate limit entries from storage", len(rate_limits))
        
        self._storage_loaded = True

    async def _save_storage(self) -> None:
        """Save tokens and rate limits to storage."""
        data = {
            "tokens": {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "access_expires": self._token_expires.isoformat() if self._token_expires else None,
                "refresh_expires": self._refresh_expires.isoformat() if self._refresh_expires else None,
            },
            "rate_limits": {
                key: {
                    "count": limit_data["count"],
                    "reset_time": limit_data["reset_time"].isoformat() if isinstance(limit_data["reset_time"], datetime) else limit_data["reset_time"],
                }
                for key, limit_data in self._rate_limits.items()
            },
        }
        
        await self._store.async_save(data)
        _LOGGER.debug("Saved tokens and rate limits to storage")

    async def _ensure_token(self) -> None:
        """Ensure we have a valid access token."""
        # Load from storage if not yet loaded
        await self._load_storage()
        
        if self._access_token and self._token_expires:
            if datetime.now() < self._token_expires:
                return  # Token still valid
        
        # Try refresh token if available
        if self._refresh_token and self._refresh_expires:
            if datetime.now() < self._refresh_expires:
                try:
                    await self._refresh_access_token()
                    return
                except Exception as err:
                    _LOGGER.warning("Failed to refresh token: %s", err)
        
        # Get new token pair
        await self._get_new_token()

    async def _get_new_token(self) -> None:
        """Get a new token pair using secret ID and key."""
        url = f"{self._base_url}/api/v2/token/new/"
        
        async with self._session.post(
            url,
            json={
                "secret_id": self._secret_id,
                "secret_key": self._secret_key,
            },
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            self._access_token = data["access"]
            self._refresh_token = data.get("refresh")
            
            # Tokens typically expire in seconds from now
            access_expires_in = data.get("access_expires", 86400)  # Default 24h
            refresh_expires_in = data.get("refresh_expires", 2592000)  # Default 30d
            
            self._token_expires = datetime.now() + timedelta(seconds=access_expires_in - 60)  # 1 min buffer
            self._refresh_expires = datetime.now() + timedelta(seconds=refresh_expires_in)
            
            _LOGGER.info(
                "New token pair obtained (access expires: %s, refresh expires: %s)",
                self._token_expires,
                self._refresh_expires,
            )
            
            # Save to storage
            await self._save_storage()

    async def _refresh_access_token(self) -> None:
        """Refresh access token using refresh token."""
        url = f"{self._base_url}/api/v2/token/refresh/"
        
        async with self._session.post(
            url,
            json={"refresh": self._refresh_token},
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            self._access_token = data["access"]
            access_expires_in = data.get("access_expires", 86400)
            self._token_expires = datetime.now() + timedelta(seconds=access_expires_in - 60)
            
            _LOGGER.info("Access token refreshed using refresh token (expires: %s)", self._token_expires)
            
            # Save to storage
            await self._save_storage()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _check_rate_limit(self, endpoint_key: str, max_per_day: int) -> bool:
        """Check if we can make a request based on rate limits."""
        # Load storage first if not yet loaded
        await self._load_storage()
        
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
            
            # Save updated rate limits to storage
            await self._save_storage()
            
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
        # Ensure we have a valid token
        await self._ensure_token()
        
        if rate_limit_key and max_per_day:
            if not await self._check_rate_limit(rate_limit_key, max_per_day):
                raise Exception(f"Rate limit exceeded for {rate_limit_key}")
        
        url = f"{self._base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                # Extract rate limit headers from GoCardless
                # Note: Headers are lowercase with underscores in aiohttp
                rate_limit_info = {}
                
                # General rate limits (per minute)
                if "http_x_ratelimit_limit" in response.headers:
                    rate_limit_info["general_limit"] = response.headers["http_x_ratelimit_limit"]
                if "http_x_ratelimit_remaining" in response.headers:
                    rate_limit_info["general_remaining"] = response.headers["http_x_ratelimit_remaining"]
                if "http_x_ratelimit_reset" in response.headers:
                    rate_limit_info["general_reset_seconds"] = response.headers["http_x_ratelimit_reset"]
                
                # Account-specific rate limits (per day)
                if "http_x_ratelimit_account_success_limit" in response.headers:
                    rate_limit_info["account_limit"] = response.headers["http_x_ratelimit_account_success_limit"]
                if "http_x_ratelimit_account_success_remaining" in response.headers:
                    rate_limit_info["account_remaining"] = response.headers["http_x_ratelimit_account_success_remaining"]
                if "http_x_ratelimit_account_success_reset" in response.headers:
                    rate_limit_info["account_reset_seconds"] = response.headers["http_x_ratelimit_account_success_reset"]
                
                if rate_limit_info:
                    _LOGGER.info(
                        "API rate limit info for %s: %s",
                        endpoint,
                        rate_limit_info,
                    )
                    
                    # Check account-specific remaining (this is the important one for daily limits)
                    if rate_limit_key and "http_x_ratelimit_account_success_remaining" in response.headers:
                        remaining = int(response.headers["http_x_ratelimit_account_success_remaining"])
                        limit = int(response.headers.get("http_x_ratelimit_account_success_limit", 0))
                        
                        _LOGGER.info(
                            "Account rate limit for %s: %d/%d remaining",
                            rate_limit_key,
                            remaining,
                            limit,
                        )
                        
                        # Warn if getting low (sandbox will show 200, real accounts show 2-10)
                        if limit < 50 and remaining <= 1:  # Real account with low remaining
                            _LOGGER.warning(
                                "LOW RATE LIMIT: Only %d requests remaining for %s (limit: %d)",
                                remaining,
                                rate_limit_key,
                                limit,
                            )
                
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

    async def get_institution(self, institution_id: str) -> dict[str, Any] | None:
        """Get details for a specific institution."""
        try:
            return await self._request("GET", f"/api/v2/institutions/{institution_id}/")
        except Exception as err:
            _LOGGER.error("Failed to get institution %s: %s", institution_id, err)
            return None

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

    async def clear_storage(self) -> None:
        """Clear stored tokens and rate limits (for testing/reset)."""
        await self._store.async_remove()
        self._access_token = None
        self._refresh_token = None
        self._token_expires = None
        self._refresh_expires = None
        self._rate_limits = {}
        self._storage_loaded = False
        _LOGGER.info("Cleared all stored tokens and rate limits")

