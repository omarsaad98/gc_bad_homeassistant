"""Optional live API smoke tests."""
from __future__ import annotations

import pytest

from custom_components.gc_bad.api.client import GoCardlessApiClient
from custom_components.gc_bad.storage import IntegrationStorage


pytestmark = [pytest.mark.asyncio, pytest.mark.live]


async def test_validate_api_key_live(hass, secret_id: str, secret_key: str) -> None:
    """Validate credentials against real API."""
    client = GoCardlessApiClient(
        hass,
        IntegrationStorage(hass, "test_live_api"),
        secret_id,
        secret_key,
    )
    assert await client.validate_api_key() is True


async def test_get_requisitions_live(hass, secret_id: str, secret_key: str) -> None:
    """Fetch requisitions from real API."""
    client = GoCardlessApiClient(
        hass,
        IntegrationStorage(hass, "test_live_api"),
        secret_id,
        secret_key,
    )
    requisitions = await client.get_requisitions()
    assert isinstance(requisitions, list)

