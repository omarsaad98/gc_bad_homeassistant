# Architecture & Implementation Details

## Overview
This integration connects Home Assistant to the GoCardless Bank Account Data API (formerly Nordigen). It is built with a focus on reliability, performance, and strict adherence to API rate limits.

## Key Technical Decisions

### 1. Rate Limit Strategy
GoCardless imposes aggressive rate limits (typically 2-4 requests per day for real accounts). 
- **Conservative Polling**: Balances and details are updated once every 24 hours.
- **Safety Buffer**: We apply a 25% safety buffer to all documented limits.
- **Header Monitoring**: The integration parses `http_x_ratelimit_account_success_limit` and related headers from every response to dynamically adjust and log current usage.
- **Pre-emptive Blocking**: Requests are blocked before being sent if the local counter indicates the limit has been reached.

### 2. Data Persistence
To minimize API usage and ensure a fast startup:
- **Token Storage**: Access and refresh tokens are stored in Home Assistant's secure storage (`.storage/`).
- **Data Caching**: Account balances and details are persisted for reuse on restart.
- **Restart Optimization**: On startup, cached data is loaded immediately and sensor state is restored. No API calls are made during startup.

### 3. Startup Behavior
1. **Cache Load**: Cached data is restored for all accounts and sensor state is restored via `RestoreSensor`.
2. **No Boot Fetches**: The coordinator does not refresh at startup.
3. **Scheduled Refreshes**: Two daily refreshes (06:00 and 18:00 local time) trigger API fetches, with a 10-hour guard to skip if a recent successful refresh already occurred.

### 4. Country & Institution Selection
- **pycountry**: Uses the `pycountry` library to provide a comprehensive and standardized list of 240+ countries.
- **Institution API**: Bank lists are fetched directly from GoCardless based on the selected country.
- **Dynamic Naming**: Sensor names are built dynamically using the official institution name and the account name provided by the bank.

## Data Structures
The internal state is managed by a `DataUpdateCoordinator` which organizes data by account ID:
```json
{
  "accounts": {
    "account_id": {
      "details": { ... },
      "balances": { ... },
      "transactions": { ... },
      "institution_id": "..."
    }
  },
  "institution_names": {
    "id": "Friendly Name"
  }
}
```


