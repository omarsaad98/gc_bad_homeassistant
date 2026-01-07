# Quick Start Guide

## Project Successfully Set Up! ✓

Your Home Assistant integration for GoCardless Bank Account Data is ready to use.

## What You Have

A fully functional Home Assistant custom integration with:
- ✓ Complete GoCardless API v2 integration
- ✓ Rate limit management (respects 2/day for balances, etc.)
- ✓ Country selection using pycountry (249 countries)
- ✓ Bank/institution selection
- ✓ OAuth flow preparation
- ✓ Balance and details sensors for all connected accounts
- ✓ Proper error handling

## Quick Commands

### Validate Integration
```powershell
uv run python validate_integration.py
```

### Activate Virtual Environment
```powershell
.venv\Scripts\Activate.ps1
```

### Check Dependencies
```powershell
uv tree
```

### Sync Dependencies
```powershell
uv sync
```

## File Structure

```
custom_components/gc_bad/
├── __init__.py           # Integration entry point
├── manifest.json         # Integration metadata
├── const.py             # Constants & rate limits
├── config_flow.py       # Setup UI (with pycountry!)
├── coordinator.py       # Data coordinator
├── api_client.py        # GoCardless API client
├── sensor.py            # Balance & details sensors
└── translations/
    └── en.json          # UI translations
```

## Key Features Implemented

### 1. Rate Limiting
The integration automatically manages GoCardless's strict rate limits:
- **Balances**: 2 requests/day → updates every 12 hours
- **Details**: 2 requests/day → updates every 12 hours
- **Transactions**: 4 requests/day → updates every 6 hours
- **Requisitions**: Updates every 30 minutes

### 2. Country Selection (pycountry)
Instead of a hardcoded list, the integration uses `pycountry` which provides:
- 249 countries automatically
- Standard ISO country codes (alpha_2)
- Official country names
- Easy maintenance (no manual updates needed)

### 3. Sensor Entities
For each bank account, you get:

**Balance Sensor**
- Shows current balance with currency
- Entity ID: `sensor.account_XXXX_balance`
- Updates respecting rate limits

**Details Sensor**
- Shows IBAN or account name
- Entity ID: `sensor.account_XXXX_details`
- Includes owner name, currency, status

## Testing the Integration

### 1. Copy to Home Assistant
```powershell
# Copy integration to your HA config
Copy-Item -Recurse custom_components\gc_bad C:\path\to\homeassistant\config\custom_components\
```

### 2. Restart Home Assistant
Restart HA to load the new integration

### 3. Add Integration
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "GoCardless Bank Account Data"
4. Enter your GoCardless API Secret Key

### 4. Add Bank Connection
1. Click **Configure** on the integration
2. Enable "Add New Bank Connection"
3. Select country (from pycountry list)
4. Select your bank
5. Complete OAuth flow

## API Secret

Get your GoCardless API secret from:
1. Sign up at https://gocardless.com
2. Navigate to Bank Account Data section
3. Generate API secret
4. Copy for use in Home Assistant

## Troubleshooting

### Rate Limit Errors
- Integration automatically respects limits
- Check logs: `home-assistant.log`
- Balances only update twice per day

### Country/Bank Selection
- Using pycountry: 249 countries available
- If bank not found, check GoCardless supported institutions

### OAuth Flow
- Current implementation prepares OAuth
- Callback URL needs production implementation
- See IMPLEMENTATION.md for details

## Documentation

- **README.md** - User guide and features
- **IMPLEMENTATION.md** - Technical details and decisions
- **SETUP_SUMMARY.md** - Complete setup overview

## Next Steps

1. **Test in Home Assistant**: Copy integration and test
2. **Get API Key**: Sign up with GoCardless
3. **Test Rate Limits**: Verify rate limiting works
4. **Add OAuth Callback**: Implement production OAuth (if needed)
5. **Customize**: Add transaction sensors, notifications, etc.

## Dependencies

All installed via uv:
```toml
aiohttp>=3.11.11       # HTTP client
homeassistant>=2024.12.5  # HA core
pycountry>=24.6.1      # Country data
```

## Support

- Check logs in Home Assistant
- Review `IMPLEMENTATION.md` for technical details
- Validate with: `uv run python validate_integration.py`

---

**Status**: Ready for development and testing!
**Project**: Fully set up with uv ✓
**Country Selection**: Using pycountry (not hardcoded) ✓
**Rate Limits**: Implemented and managed ✓

