# Lifecycle

## Setup

During config entry setup:

1. `__init__.py` reads credentials from `ConfigEntry.data`.
2. Runtime objects are created:
   - `IntegrationStorage`
   - `GoCardlessApiClient`
   - `GoCardlessDataUpdateCoordinator`
3. Runtime objects are stored on `ConfigEntry.runtime_data`.
4. Scheduled refresh callbacks are registered.
5. `coordinator.async_config_entry_first_refresh()` runs.
6. Sensor platform setup is forwarded.

## Refresh

- Coordinator owns refresh behavior.
- Scheduled refreshes run at configured hours.
- Skip window logic avoids redundant refreshes shortly after a successful one.

## Options Flow

- Options flow can create a new requisition and complete authorization.
- On options update, Home Assistant reloads the config entry via update listener.
- Reload triggers a full coordinator refresh with the current account set.

## Unload

On unload:

1. Sensor platforms are unloaded.
2. Scheduled callbacks are unsubscribed.
3. Runtime data is removed from `hass.data`.

## Reload

Reload is delegated to Home Assistant config entry reload (`async_reload`).
