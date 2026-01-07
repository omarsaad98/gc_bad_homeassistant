# GoCardless Bank Account Data - Home Assistant Integration

A Home Assistant custom integration for accessing bank account data through the GoCardless Bank Account Data API.

## Features

- 🏦 **Multiple Bank Accounts**: View balances and details from all connected bank accounts
- 🌍 **Multi-Country Support**: Connect banks from any country using pycountry
- 🔐 **OAuth Flow**: Secure bank connection through OAuth2
- ⏱️ **Rate Limit Management**: Intelligent rate limiting to comply with GoCardless API restrictions
- 📊 **Real-time Data**: Account balances, details, and transaction data
- 🔄 **Easy Setup**: Simple configuration through Home Assistant UI

## Rate Limits

The integration is designed to respect GoCardless's aggressive rate limits:

- **Account Balances**: Max 2 requests per day (updates every 12 hours)
- **Account Details**: Max 2 requests per day (updates every 12 hours)
- **Account Transactions**: Max 4 requests per day (updates every 6 hours)
- **Requisitions List**: Updates every 30 minutes

## Installation

### Using uv (Development)

1. Clone this repository
2. Install dependencies:
   ```bash
   uv sync
   ```

### Manual Installation

1. Copy the `custom_components/gc_bad` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

### HACS (Future)

This integration may be available through HACS in the future.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "GoCardless Bank Account Data"
3. Enter your GoCardless API Secret Key
4. Click Submit

### Getting Your API Secret

1. Sign up for a GoCardless account at [https://gocardless.com](https://gocardless.com)
2. Navigate to the Bank Account Data section
3. Generate an API secret key
4. Copy the secret key for use in Home Assistant

## Adding Bank Connections

After initial setup, you can add bank connections (requisitions):

1. Go to **Settings** → **Devices & Services**
2. Find the "GoCardless Bank Account Data" integration
3. Click **Configure**
4. Select **Add New Bank Connection**
5. Choose your country
6. Select your bank from the list
7. Complete the OAuth flow with your bank

## Sensors

The integration creates the following sensors for each connected bank account:

### Account Balance Sensor
- **Entity ID**: `sensor.account_XXXX_balance`
- **State**: Current account balance
- **Attributes**:
  - Account ID
  - Requisition ID
  - Institution ID
  - Balance type
  - Reference date

### Account Details Sensor
- **Entity ID**: `sensor.account_XXXX_details`
- **State**: IBAN or account name
- **Attributes**:
  - Account ID
  - IBAN
  - Account name
  - Currency
  - Owner name
  - Account status

## API Documentation

This integration uses the GoCardless Bank Account Data API v2. For more information:
- [GoCardless API Documentation](https://developer.gocardless.com/bank-account-data/overview)
- [API Reference](https://developer.gocardless.com/api-reference)

## Development

### Project Structure

```
custom_components/gc_bad/
├── __init__.py           # Integration setup
├── manifest.json         # Integration manifest
├── const.py             # Constants and configuration
├── config_flow.py       # Configuration flow (UI setup)
├── coordinator.py       # Data update coordinator
├── api_client.py        # GoCardless API client
├── sensor.py            # Sensor entities
└── strings.json         # UI strings
```

### Requirements

- Python 3.12+
- Home Assistant 2024.12+
- GoCardless API Secret

### Dependencies

- `homeassistant` - Home Assistant core
- `aiohttp` - Async HTTP client
- `pycountry` - Country codes and names

## Troubleshooting

### Rate Limit Errors

If you encounter rate limit errors:
- The integration automatically respects rate limits
- Balance updates are limited to twice per day
- Check logs for rate limit messages

### Authentication Issues

If authentication fails:
- Verify your API secret key is correct
- Ensure your GoCardless account is active
- Check the Home Assistant logs for detailed error messages

### No Institutions Found

If no banks appear for your country:
- Verify the country code is correct
- Check if GoCardless supports banks in your country
- Refer to [GoCardless supported institutions](https://gocardless.com/bank-account-data/institutions/)

## License

This project is licensed under the MIT License.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the Home Assistant community forums

## Disclaimer

This is a third-party integration and is not affiliated with or endorsed by GoCardless. Use at your own risk.

