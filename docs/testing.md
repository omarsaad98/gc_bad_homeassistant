# Testing Guide

## Overview
This project includes a robust testing suite designed to validate the integration against the real GoCardless API without risking your daily rate limits.

## Setup for Testing
1. Create a `.env` file in the project root (use `.env.example` as a template).
2. Add your `GCD_SECRET_ID` and `GCD_SECRET_KEY`.
3. Ensure you have `uv` installed.

## Safe Testing with Sandbox
**Always use the Sandbox institution for development testing.**
- **Institution ID**: `SANDBOXFINANCE_SFIN0000`
- **Benefits**: No rate limits, realistic fake data, instant authorization.

### Interactive Sandbox Test
Run the following command to guide you through creating a sandbox connection and fetching data:
```bash
uv run python tests/connect_sandbox.py
```

## Automated Tests
Run the automated test suite using `uv`:

### Basic Checks (No API required)
```bash
uv run pytest tests/test_basic.py -v
```

### Live API Client Tests
```bash
uv run pytest tests/test_api_client_live.py -v
```

### Integration Setup Tests
```bash
uv run pytest tests/test_integration_live.py -v
```

## Manual Debugging
Use the manual test script for a comprehensive check of all features:
```bash
uv run python tests/manual_test_script.py
```

## API Response Logs
When running tests, raw API responses are saved to:
`tests/test_data/api_responses/`

These are invaluable for reviewing the exact data structure returned by your bank.

## Resetting Rate Limits (Testing Only)
If you hit your local rate limit counters during testing, you can reset them with:
```bash
uv run python tests/reset_rate_limits.py
```


