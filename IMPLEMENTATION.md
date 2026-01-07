# Implementation Documentation

## Project Overview

This is a Home Assistant custom integration for the GoCardless Bank Account Data API. It allows users to view their bank account balances and details from multiple banks across different countries.

## Technical Decisions

### Rate Limiting Strategy

GoCardless imposes aggressive rate limits on their API:
- **Account Balances**: 10 requests/day (reducing to 4/day in future) - We use 2/day conservatively
- **Account Details**: 10 requests/day (reducing to 4/day in future) - We use 2/day conservatively  
- **Account Transactions**: 4 requests/day

**Implementation**:
- Rate limiting is tracked per account per endpoint in `api_client.py`
- Update intervals are set in `const.py` based on these limits
- Sensors track their last update time and skip updates if called too frequently
- Rate limit counters reset every 24 hours

### Country Selection

**Decision**: Use `pycountry` library instead of hardcoded country list

**Rationale**:
- Provides comprehensive, maintained list of all countries
- Automatically includes country codes (alpha_2) and names
- Easier to maintain - no need to manually update list
- More flexible for future expansion

**Implementation**: `config_flow.py` uses `pycountry.countries` to generate country choices

### OAuth Flow

The integration uses Home Assistant's external step mechanism for OAuth:
1. User selects country and bank in config flow
2. Integration creates a requisition via GoCardless API
3. User is redirected to bank's authorization page
4. After authorization, user returns to Home Assistant
5. Integration completes setup

**Note**: The callback URL handling needs to be implemented for production use.

### Data Structure

The coordinator maintains data in the following structure:

```python
{
    "requisitions": [
        {
            "id": "requisition_id",
            "status": "LN",  # Linked
            "institution_id": "bank_id",
            "accounts": ["account_id_1", "account_id_2"]
        }
    ],
    "accounts": {
        "account_id": {
            "id": "account_id",
            "requisition_id": "requisition_id",
            "institution_id": "bank_id",
            "details": {...},  # Account details (IBAN, name, etc.)
            "balances": {...},  # Current balances
            "transactions": {...}  # Transaction history
        }
    }
}
```

### Sensor Design

Two sensor types per account:
1. **Balance Sensor**: Shows current account balance with currency
2. **Details Sensor**: Shows IBAN/account name with additional metadata

Both sensors:
- Extend `CoordinatorEntity` for efficient updates
- Track last update time to respect rate limits
- Provide rich attributes for automation use

### Error Handling

- API errors are logged and gracefully handled
- Rate limit errors (429) are specifically detected
- Authentication errors (401) are handled separately
- Invalid API responses don't crash the integration

## File Structure

```
custom_components/gc_bad/
├── __init__.py           # Integration setup and entry point
├── manifest.json         # Integration metadata
├── const.py             # Constants and rate limit configuration
├── config_flow.py       # UI configuration flow
├── coordinator.py       # Data update coordinator
├── api_client.py        # GoCardless API client with rate limiting
├── sensor.py            # Sensor platform implementation
├── strings.json         # UI strings (deprecated, use translations)
└── translations/
    └── en.json          # English translations
```

## Dependencies

- `homeassistant>=2024.12.5` - Core framework
- `aiohttp>=3.11.11` - Async HTTP client
- `pycountry>=24.6.1` - Country codes and names

## Configuration Storage

- API secret is stored securely in Home Assistant's config entry
- Rate limit tracking is stored in memory (resets on restart)
- Account data is fetched from API on each coordinator update

## Future Improvements

### Potential Enhancements

1. **Transaction History Sensor**: Add dedicated sensor for recent transactions
2. **Callback Handler**: Implement proper OAuth callback endpoint
3. **Rate Limit Persistence**: Store rate limit counters in Home Assistant storage
4. **Institution Caching**: Cache institution lists to reduce API calls
5. **Multi-Account Cards**: Create device entries for better organization
6. **Notification Service**: Alert on low balance or unusual transactions
7. **Historical Data**: Store and chart balance history over time

### Known Limitations

1. **OAuth Callback**: Currently uses placeholder URL - needs proper implementation
2. **Transaction Display**: Transactions are fetched but not yet displayed in sensors
3. **Requisition Status**: Only "Linked" (LN) requisitions are processed
4. **Error Recovery**: No automatic retry for failed requisitions

## Testing Considerations

When testing this integration:
1. Use GoCardless sandbox environment to avoid affecting real accounts
2. Be mindful of rate limits even in testing
3. Test with multiple banks/countries to ensure broad compatibility
4. Verify rate limit tracking works across restarts
5. Test OAuth flow completion

## API Reference

- Base URL: `https://bankaccountdata.gocardless.com`
- API Version: v2
- Documentation: https://developer.gocardless.com/bank-account-data/overview

### Key Endpoints Used

- `GET /api/v2/requisitions/` - List all requisitions
- `GET /api/v2/requisitions/{id}/` - Get specific requisition
- `POST /api/v2/requisitions/` - Create new requisition
- `GET /api/v2/institutions/?country={code}` - List banks by country
- `GET /api/v2/accounts/{id}/details/` - Get account details
- `GET /api/v2/accounts/{id}/balances/` - Get account balances
- `GET /api/v2/accounts/{id}/transactions/` - Get transactions

## Maintenance Notes

- Monitor GoCardless API changes and rate limit updates
- Keep pycountry updated for accurate country data
- Update Home Assistant minimum version as needed for new features
- Review and update rate limits if GoCardless changes their policies

