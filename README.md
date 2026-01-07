# GoCardless Bank Account Data for Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)]()
[![Built with uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A robust Home Assistant custom integration for accessing bank account data through the GoCardless (formerly Nordigen) Bank Account Data API.

## Features

- 🏦 **Multiple Bank Accounts**: Automatically discovers and tracks all accounts across connected institutions.
- 🌍 **Global Support**: Connect to 2,000+ banks across 30+ countries.
- 🔐 **Secure OAuth2**: Built-in flow for secure bank authorization.
- 🛡️ **Rate Limit Protection**: Advanced tracking and pre-emptive blocking to strictly adhere to GoCardless's aggressive daily limits.
- 🔄 **State Persistence**: Tokens and account data survive Home Assistant restarts, ensuring instant data availability and zero-startup API overhead.
- 📊 **Rich Sensor Data**: Provides balances, IBANs, owner names, and metadata for every account.

## Installation

### Manual Installation
1. Copy the `custom_components/gc_bad` directory to your Home Assistant's `custom_components` directory.
2. Restart Home Assistant.

### HACS
*Coming soon!*

## Configuration

1. Go to **Settings** → **Devices & Services**.
2. Click **Add Integration** and search for "GoCardless Bank Account Data".
3. Enter your **Secret ID** and **Secret Key**.
   - *Get these from the [GoCardless Developer Dashboard](https://gocardless.com).*
4. To add specific banks, click **Configure** on the integration card and select **Add New Bank Connection**.

## Usage

The integration creates two primary sensors for each account:

### 1. Balance Sensor
- **State**: Current balance amount.
- **Attributes**: Account ID, Institution, Balance Type, Reference Date.

### 2. Details Sensor
- **State**: Account IBAN or Name.
- **Attributes**: Owner Name, Currency, Account Type, Product.

## Documentation

For more detailed information, please see:
- [Architecture & Implementation](docs/architecture.md)
- [OAuth & Bank Connections](docs/oauth.md)
- [Testing & Development](docs/testing.md)

## Requirements

- Home Assistant 2024.12+
- Python 3.12+
- A valid GoCardless Secret ID and Secret Key.

## ⚠️ Warning

**This project was entirely vibe coded.** 

What does that mean? It means this integration was built through a combination of:
- Reading API docs when things broke
- Trial and error
- "This feels right" moments
- Debugging in production
- Occasional web searches when stuck

While it works (mostly), it may not follow all best practices, have comprehensive error handling everywhere, or be optimized for every edge case. Use at your own risk, and feel free to submit issues or PRs if you find problems or want to improve things.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Disclaimer: This is a third-party integration and is not affiliated with or endorsed by GoCardless.*
