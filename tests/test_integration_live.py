"""Live integration tests for the full integration setup."""
from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows event loop policy (required for aiodns)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.gc_bad.const import CONF_SECRET_ID, CONF_SECRET_KEY, DOMAIN
from tests.conftest import save_api_response


@pytest.mark.asyncio
class TestLiveIntegration:
    """Test the full integration with real API."""

    async def test_integration_setup(
        self, hass: HomeAssistant, secret_id: str, secret_key: str, response_logger
    ):
        """Test that the integration sets up correctly with real API."""
        print("\n\n=== Testing Integration Setup ===")
        
        # Create config entry
        from unittest.mock import Mock
        from homeassistant.config_entries import ConfigEntry
        
        config_entry = Mock(spec=ConfigEntry)
        config_entry.domain = DOMAIN
        config_entry.data = {
            CONF_SECRET_ID: secret_id,
            CONF_SECRET_KEY: secret_key,
        }
        config_entry.entry_id = "test_integration"
        config_entry.add_to_hass(hass)
        
        # Set up the integration
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        
        # Set up the config entry
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        
        print("✓ Integration setup successful")
        
        # Check that data is stored
        assert DOMAIN in hass.data
        assert config_entry.entry_id in hass.data[DOMAIN]
        print("✓ Integration data stored correctly")
        
        # Check coordinator
        coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
        print(f"✓ Coordinator created: {coordinator}")
        
        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()
        print("✓ Initial data fetch successful")
        
        if coordinator.data:
            requisitions = coordinator.data.get("requisitions", [])
            accounts = coordinator.data.get("accounts", {})
            
            print(f"\nData retrieved:")
            print(f"  Requisitions: {len(requisitions)}")
            print(f"  Accounts: {len(accounts)}")
            
            response_logger("coordinator_initial_data", coordinator.data)
            
            for req in requisitions:
                print(f"    - {req.get('id')}: {req.get('status')}")

    async def test_sensor_creation(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test that sensors are created for accounts."""
        print("\n\n=== Testing Sensor Creation ===")
        
        # Set up integration
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_API_SECRET: api_secret},
            entry_id="test_sensors",
        )
        config_entry.add_to_hass(hass)
        
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        
        # Wait for sensors to be created
        await hass.async_block_till_done()
        
        # Check for sensor entities
        states = hass.states.async_all()
        gc_sensors = [s for s in states if s.entity_id.startswith("sensor.account_")]
        
        print(f"✓ Found {len(gc_sensors)} GoCardless sensors")
        
        sensor_data = []
        for state in gc_sensors:
            print(f"\n  Sensor: {state.entity_id}")
            print(f"    State: {state.state}")
            print(f"    Attributes: {dict(state.attributes)}")
            
            sensor_data.append({
                "entity_id": state.entity_id,
                "state": state.state,
                "attributes": dict(state.attributes),
            })
        
        if sensor_data:
            response_logger("sensors_created", {"count": len(sensor_data), "sensors": sensor_data})

    async def test_coordinator_updates(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test that coordinator updates work correctly."""
        print("\n\n=== Testing Coordinator Updates ===")
        
        # Set up integration
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_API_SECRET: api_secret},
            entry_id="test_coordinator_updates",
        )
        config_entry.add_to_hass(hass)
        
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        
        coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
        
        # Trigger an update
        print("Triggering coordinator update...")
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        
        print("✓ Coordinator update completed")
        
        if coordinator.data:
            accounts = coordinator.data.get("accounts", {})
            print(f"  Accounts after update: {len(accounts)}")
            
            # Try updating specific account data
            if accounts:
                account_id = list(accounts.keys())[0]
                print(f"\nUpdating details for account {account_id}...")
                
                details = await coordinator.async_update_account_details(account_id)
                if details:
                    print("✓ Account details updated")
                    response_logger(f"coordinator_update_details_{account_id}", details)

