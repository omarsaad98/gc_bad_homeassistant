"""The GoCardless Bank Account Data integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .api.client import GoCardlessApiClient
from .const import (
    CONF_SECRET_ID,
    CONF_SECRET_KEY,
    DOMAIN,
    REFRESH_SKIP_WINDOW,
    SCHEDULED_REFRESH_HOURS,
)
from .coordinator import GoCardlessDataUpdateCoordinator
from .storage import IntegrationStorage
from .views import GoCardlessAuthCallbackView

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(slots=True)
class GCBadRuntimeData:
    """Runtime objects for one config entry."""

    coordinator: GoCardlessDataUpdateCoordinator
    api_client: GoCardlessApiClient
    storage: IntegrationStorage
    unsub_schedules: list[Callable[[], None]] = field(default_factory=list)


type GCBadConfigEntry = ConfigEntry[GCBadRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration domain."""
    hass.http.register_view(GoCardlessAuthCallbackView(hass))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GCBadConfigEntry) -> bool:
    """Set up GoCardless from a config entry."""
    secret_id = entry.data[CONF_SECRET_ID]
    secret_key = entry.data[CONF_SECRET_KEY]
    storage = IntegrationStorage(hass, entry.entry_id)
    api_client = GoCardlessApiClient(hass, storage, secret_id, secret_key)
    coordinator = GoCardlessDataUpdateCoordinator(hass, api_client, storage)
    runtime_data = GCBadRuntimeData(
        coordinator=coordinator,
        api_client=api_client,
        storage=storage,
    )

    entry.runtime_data = runtime_data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = runtime_data
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    @callback
    def _schedule_refresh(_call_time) -> None:
        last_refresh = coordinator.last_successful_refresh
        if last_refresh and dt_util.utcnow() - last_refresh < REFRESH_SKIP_WINDOW:
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
        runtime_data.unsub_schedules.append(unsub)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GCBadConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime_data = entry.runtime_data
    for unsub in runtime_data.unsub_schedules:
        unsub()

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: GCBadConfigEntry,
) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
