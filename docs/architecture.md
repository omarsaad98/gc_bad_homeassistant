# Architecture

## Mental Model

The integration follows a simple flow:

1. Config flow stores credentials.
2. Integration setup builds runtime objects.
3. Coordinator fetches and normalizes API data into one snapshot.
4. Sensor entities project that snapshot into Home Assistant states.

## Module Boundaries

### `custom_components/gc_bad/__init__.py`

- Entry lifecycle only (setup, unload, reload)
- Runtime object wiring
- Scheduled refresh registration

### `custom_components/gc_bad/config_flow.py` and `custom_components/gc_bad/views.py`

- User setup and bank authorization flow
- No entity/coordinator business logic

### `custom_components/gc_bad/api/`

- `auth.py`: token lifecycle
- `rate_limits.py`: daily limit accounting and persistence
- `client.py`: endpoint methods and request transport

### `custom_components/gc_bad/coordinator.py`

- Owns the integration snapshot
- Handles all API-to-model orchestration
- Persists snapshot using storage boundary

### `custom_components/gc_bad/entity.py` and `custom_components/gc_bad/sensor.py`

- Base entity account lookup helpers
- Balance sensors only
- No API calls from entities

### `custom_components/gc_bad/storage.py`

- Encapsulates persistence schema for:
  - API state (tokens and rate limits)
  - coordinator snapshot cache

## Snapshot Data Model

`IntegrationSnapshot`:
- `accounts: dict[str, AccountSnapshot]`
- `institution_names: dict[str, str]`
- `last_successful_refresh: str | None`

`AccountSnapshot`:
- account identity and linkage (`id`, `requisition_id`, `institution_id`)
- details payload plus derived fields (`account_name`, `iban`)
- list of typed `BalanceSnapshot` entries

`BalanceSnapshot`:
- `amount`, `currency`, `balance_type`, `reference_date`

## Complexity Rules

- Keep modules single-purpose.
- Keep entities read-only over coordinator snapshot.
- Keep API state and snapshot persistence isolated in `storage.py`.
- Prefer explicit typed models over nested ad-hoc dict access.


