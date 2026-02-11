# GoCardless Bank Account Data for Home Assistant

Custom Home Assistant integration for GoCardless Bank Account Data (formerly Nordigen).

## What It Does

- Connects Home Assistant to GoCardless using Secret ID and Secret Key.
- Lets you add bank connections through an OAuth authorization flow.
- Creates monetary balance sensors for each discovered account balance.
- Persists API/auth state and cached account snapshots across restarts.

## Installation

1. Copy `custom_components/gc_bad` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. In Home Assistant, go to **Settings -> Devices & Services -> Add Integration**.
4. Add **GoCardless Bank Account Data** and provide `secret_id` + `secret_key`.

## Configuration

- Initial setup stores credentials in `ConfigEntry.data`.
- Bank connections are added from the integration options flow.
- Options flow stores linked requisition IDs in `ConfigEntry.options`.

## Entities

The integration currently creates **balance sensors only**.

Each balance sensor exposes:
- state: monetary balance amount
- unit: balance currency
- attributes: account ID, requisition ID, institution ID, IBAN, balance type, reference date, refresh metadata

## Documentation

- [Architecture](docs/architecture.md)
- [Lifecycle](docs/lifecycle.md)
- [Error Model](docs/error_model.md)
- [Developer Guide](docs/developer_guide.md)
- [OAuth Flow](docs/oauth.md)
- [Testing](docs/testing.md)

## License

This project is licensed under GNUv3. See [LICENSE](LICENSE).
