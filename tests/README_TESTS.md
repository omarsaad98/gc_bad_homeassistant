# Testing Guide

## Quick Setup

### 1. Create .env File

```powershell
# Copy the example file
Copy-Item .env.example .env
```

### 2. Add Your Credentials

Edit `.env` in the project root and add your GoCardless credentials:

```env
GCD_SECRET_ID=your-actual-secret-id-here
GCD_SECRET_KEY=your-actual-secret-key-here
```

**That's it!** All tests automatically load from `.env`.

## Running Tests

### Manual Test Script (Recommended)

```powershell
uv run python tests/manual_test_script.py
```

This will:
- Load credentials from `.env` automatically
- Test all API endpoints with real API
- Save responses to `tests/test_data/api_responses/`
- Display detailed output with results

### Basic Tests (No API needed)

```powershell
cd tests
python test_basic.py
```

Tests:
- Constants defined correctly
- Country data (pycountry)
- Manifest structure
- File structure

## Test Output

### API Response Logs

All API responses saved to timestamped JSON files:

```
tests/test_data/api_responses/
├── 20250107_153045_manual_requisitions.json
├── 20250107_153046_manual_institutions_GB.json
├── 20250107_153047_manual_details_acc_abc123.json
└── 20250107_153048_manual_balances_acc_abc123.json
```

### Token Storage

Access and refresh tokens saved with expiry:

```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "access_expires": "2025-01-08T15:30:45",
  "refresh_expires": "2025-02-07T15:30:45",
  "saved_at": "2025-01-07T15:30:45"
}
```

## Troubleshooting

### "Missing credentials" Error

Make sure your `.env` file exists in the project root with both values:

```env
GCD_SECRET_ID=abc123...
GCD_SECRET_KEY=xyz789...
```

### 401 Unauthorized Error

- Check that your credentials are correct
- Verify no extra spaces or newlines
- Make sure your GoCardless account is active

### "No linked accounts"

- Normal if you haven't connected banks yet
- Tests will skip gracefully
- Connect a bank through Home Assistant first for full testing

### Rate Limit Warnings

- Expected behavior - tests respect rate limits
- Balances: 2 requests/day
- Wait 24 hours to reset counters

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures, loads .env
├── manual_test_script.py    # Interactive API testing
├── test_basic.py            # Basic structure tests
├── test_api_client_live.py  # Live API tests
├── test_config_flow.py      # Config flow tests
├── test_integration_live.py # Integration tests
└── test_data/              # Generated data (gitignored)
    ├── api_responses/      # JSON responses
    └── tokens.json         # Access tokens
```

## Security

- `.env` is in `.gitignore` - safe from commits
- `.env.example` is safe to commit (no real credentials)
- `tests/test_data/` is gitignored
- Never commit real credentials

## Advanced

### Using Environment Variables Instead

If you prefer environment variables over `.env`:

```powershell
$env:GCD_SECRET_ID = "your-id"
$env:GCD_SECRET_KEY = "your-key"
uv run python tests/manual_test_script.py
```

### Running Specific Tests

```powershell
# Just test constants
python -c "import tests.test_basic; tests.test_basic.test_constants()"

# Test country data
python -c "import tests.test_basic; tests.test_basic.test_get_countries()"
```

## Next Steps

After successful test run:

1. Review saved API responses
2. Verify account data looks correct
3. Check rate limit tracking
4. Ready to deploy to Home Assistant!

---

**Questions?** See `QUICK_TEST_GUIDE.md` for a minimal guide or `CREDENTIALS_SETUP.md` for credential details.
