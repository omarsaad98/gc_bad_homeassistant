"""Unit tests for API client response handling."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.gc_bad.api.client import GCBadResponseError, GoCardlessApiClient


@pytest.mark.asyncio
async def test_get_requisitions_validates_payload() -> None:
    """Client should reject malformed requisition payloads."""
    client = object.__new__(GoCardlessApiClient)
    client._request = AsyncMock(return_value={"results": "bad"})  # type: ignore[method-assign]

    with pytest.raises(GCBadResponseError):
        await client.get_requisitions()


@pytest.mark.asyncio
async def test_validate_api_key_handles_api_errors() -> None:
    """Credential validation should return False on API failure."""
    client = object.__new__(GoCardlessApiClient)
    client.get_requisitions = AsyncMock(side_effect=GCBadResponseError("bad"))  # type: ignore[method-assign]

    assert await client.validate_api_key() is False
