"""Tests for config flow (without live API)."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows event loop policy (required for aiodns)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gc_bad.config_flow import get_countries
from custom_components.gc_bad.const import CONF_SECRET_ID, CONF_SECRET_KEY, DOMAIN


def test_get_countries():
    """Test that get_countries returns a dict of countries."""
    countries = get_countries()
    
    assert isinstance(countries, dict)
    assert len(countries) > 200  # Should have most countries
    assert "US" in countries
    assert "GB" in countries
    assert "DE" in countries
    assert countries["US"] == "United States"
    assert countries["GB"] == "United Kingdom"
    
    print(f"\n✓ get_countries() returns {len(countries)} countries")


@pytest.mark.asyncio
class TestConfigFlow:
    """Test the config flow."""

    async def test_user_flow_invalid_api_key(self, hass: HomeAssistant):
        """Test user flow with invalid API key."""
        print("\n\n=== Testing Config Flow with Invalid API Key ===")
        
        with patch(
            "custom_components.gc_bad.config_flow.GoCardlessAPIClient.validate_api_key",
            return_value=False,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            
            # Submit with invalid credentials
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    CONF_SECRET_ID: "invalid_id",
                    CONF_SECRET_KEY: "invalid_key",
                },
            )
            
            assert result["type"] == FlowResultType.FORM
            assert result["errors"] == {"base": "invalid_auth"}
            
            print("✓ Invalid API key rejected correctly")

    async def test_user_flow_valid_api_key(self, hass: HomeAssistant):
        """Test user flow with valid API key."""
        print("\n\n=== Testing Config Flow with Valid API Key ===")
        
        with patch(
            "custom_components.gc_bad.config_flow.GoCardlessAPIClient.validate_api_key",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            # Submit with valid credentials
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    CONF_SECRET_ID: "valid_secret_id",
                    CONF_SECRET_KEY: "valid_secret_key",
                },
            )
            
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "GoCardless Bank Account Data"
            assert result["data"] == {
                CONF_SECRET_ID: "valid_secret_id",
                CONF_SECRET_KEY: "valid_secret_key",
            }
            
            print("✓ Valid API key accepted and entry created")

    async def test_user_flow_already_configured(self, hass: HomeAssistant):
        """Test that only one instance can be configured."""
        print("\n\n=== Testing Duplicate Configuration Prevention ===")
        
        # Create an existing entry
        from pytest_homeassistant_custom_component.common import MockConfigEntry
        
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_SECRET_ID: "existing_secret_id",
                CONF_SECRET_KEY: "existing_secret_key",
            },
            unique_id="existing_secret_id",
        )
        existing_entry.add_to_hass(hass)
        
        with patch(
            "custom_components.gc_bad.config_flow.GoCardlessAPIClient.validate_api_key",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            # Try to add with same credentials
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    CONF_SECRET_ID: "existing_secret_id",
                    CONF_SECRET_KEY: "existing_secret_key",
                },
            )
            
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "already_configured"
            
            print("✓ Duplicate configuration prevented correctly")

    async def test_options_flow_init(self, hass: HomeAssistant):
        """Test options flow initialization."""
        print("\n\n=== Testing Options Flow ===")
        
        from pytest_homeassistant_custom_component.common import MockConfigEntry
        
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_SECRET_ID: "test_secret_id",
                CONF_SECRET_KEY: "test_secret_key",
            },
        )
        config_entry.add_to_hass(hass)
        
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"
        
        print("✓ Options flow initializes correctly")

