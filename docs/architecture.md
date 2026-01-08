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
- **Data Caching**: All account balances, details, and institution names are persisted.
- **Restart Optimization**: On startup, the integration loads cached data immediately. No API calls for balances or details are made during startup unless the cache is missing.

### 3. Startup Behavior
1. **Requisitions List**: One API call is made to get the current list of connections (high rate limit, safe).
2. **Cache Load**: Cached data is restored for all accounts.
3. **Lazy Fetching**: If data is missing for any account, a fetch is scheduled with a random delay (5-40s) to prevent a burst of requests.

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


