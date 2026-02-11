"""Optional live integration setup smoke tests."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.live]


async def test_integration_setup_live(hass, secret_id: str, secret_key: str) -> None:
    """Integration should set up with real credentials."""
    # Without HA test helper package, keep live integration test as an explicit placeholder.
    pytest.skip(
        "Requires pytest-homeassistant-custom-component to create MockConfigEntry"
    )

