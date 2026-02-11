"""The GoCardless Bank Account Data integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .api_client import GoCardlessAPIClient
from .const import (
    CONF_SECRET_ID,
    CONF_SECRET_KEY,
    DOMAIN,
    REFRESH_SKIP_WINDOW,
    SCHEDULED_REFRESH_HOURS,
    UPDATE_INTERVAL_BALANCES,
)
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

    # Load cached data without calling the API
    await coordinator.async_load_cached_data()

    should_force_balance_refresh = True
    if coordinator.data and coordinator.data.get("accounts"):
        now = dt_util.utcnow()
        has_recent_balance = False
        for account_data in coordinator.data["accounts"].values():
            balances = account_data.get("balances")
            if not balances:
                continue
            updated_at = account_data.get("balances_updated")
            if not updated_at:
                continue
            parsed = dt_util.parse_datetime(updated_at)
            if parsed and now - parsed < UPDATE_INTERVAL_BALANCES:
                has_recent_balance = True
                break

        if has_recent_balance:
            should_force_balance_refresh = False

    if should_force_balance_refresh:
        # Ensure balances are refreshed so new balance types appear on reload
        await coordinator.async_force_refresh_balances()
    else:
        _LOGGER.debug(
            "Skipping forced balance refresh; cached balances are recent"
        )

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
        "unsub_schedules": [],
    }

    @callback
    def _schedule_refresh(call_time) -> None:
        """Request a coordinator refresh on the configured schedule."""
        last_refresh = coordinator.last_successful_refresh
        if last_refresh and dt_util.utcnow() - last_refresh < REFRESH_SKIP_WINDOW:
            _LOGGER.debug(
                "Skipping scheduled refresh; last success %s ago",
                dt_util.utcnow() - last_refresh,
            )
            return

        hass.async_create_task(coordinator.async_request_refresh())

    for hour in SCHEDULED_REFRESH_HOURS:
        unsub = async_track_time_change(
            hass,
            _schedule_refresh,
            hour=hour,
            minute=0,
            second=0,
        )
        hass.data[DOMAIN][entry.entry_id]["unsub_schedules"].append(unsub)
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        for unsub in hass.data[DOMAIN][entry.entry_id].get("unsub_schedules", []):
            unsub()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
