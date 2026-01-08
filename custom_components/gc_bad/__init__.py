"""The GoCardless Bank Account Data integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api_client import GoCardlessAPIClient
from .const import CONF_SECRET_ID, CONF_SECRET_KEY, DOMAIN
from .coordinator import GoCardlessDataUpdateCoordinator
from .views import GoCardlessAuthCallbackView

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the GoCardless Bank Account Data component."""
    # Register the OAuth callback view
    hass.http.register_view(GoCardlessAuthCallbackView(hass))
    _LOGGER.info("Registered GoCardless OAuth callback view")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GoCardless Bank Account Data from a config entry."""
    # Get credentials from config entry
    secret_id = entry.data[CONF_SECRET_ID]
    secret_key = entry.data[CONF_SECRET_KEY]
    
    # Create API client
    api_client = GoCardlessAPIClient(hass, secret_id, secret_key)
    
    # Create data update coordinator
    coordinator = GoCardlessDataUpdateCoordinator(hass, api_client, entry.entry_id)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Ensure all accounts have details before creating sensors
    # This is needed for proper sensor naming and unique_ids
    if coordinator.data and "accounts" in coordinator.data:
        for account_id in coordinator.data["accounts"]:
            account_data = coordinator.data["accounts"][account_id]
            if not account_data.get("details"):
                _LOGGER.info("Fetching details for account %s before sensor creation", account_id)
                await coordinator.async_update_account_details(account_id)
    
    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
    }
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
