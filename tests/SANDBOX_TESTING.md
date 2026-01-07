# Sandbox Testing Guide

## Quick Start

Run the sandbox connection test:

```powershell
uv run python tests/connect_sandbox.py
```

This interactive script will:
1. Check for existing sandbox connections
2. Create a new one if needed
3. Guide you through authorization
4. Fetch all account data (details, balances, transactions)
5. Save responses for review

## What is Sandbox Finance?

**Institution ID:** `SANDBOXFINANCE_SFIN0000`

Sandbox Finance is a test bank provided by GoCardless that:
- ✅ Has **NO rate limits** (test unlimited times!)
- ✅ Returns realistic fake data
- ✅ Simulates real bank behavior
- ✅ Never affects your real accounts
- ✅ Perfect for development and testing

## Step-by-Step Process

### 1. Run the Test

```powershell
uv run python tests/connect_sandbox.py
```

### 2. Follow the Prompts

The script will:
- Check if you have existing sandbox connections
- Ask if you want to use existing or create new
- Create a requisition if needed

### 3. Authorization

When you see:

```
[ACTION REQUIRED]
Open this link in your browser to authorize:

  https://bankaccountdata.gocardless.com/psd2/start/...

After authorizing, press Enter to continue...
```

1. **Copy the URL** and open in your browser
2. You'll see the GoCardless authorization page
3. For sandbox, you can use any credentials
4. Complete the flow
5. Return to terminal and **press Enter**

### 4. View Results

The script will fetch:
- ✅ Account details (IBAN, name, currency)
- ✅ Account balances (available, booked, etc.)
- ✅ Transactions (booked and pending)

Example output:

```
--- Account 1/2 ---
Account ID: abc123...

Fetching details...
  [OK] IBAN: GB33BUKB20201555555555
  [OK] Name: Main Account
  [OK] Currency: GBP
  [OK] Status: enabled

Fetching balances...
  [OK] Found 2 balance(s):
       closingBooked: 1000.00 GBP
       expected: 950.00 GBP

Fetching transactions...
  [OK] Booked transactions: 15
  [OK] Pending transactions: 2

  Recent transactions:
    - -50.00 GBP: Coffee Shop
    - -25.00 GBP: Grocery Store
    - 1000.00 GBP: Salary Payment
```

### 5. Review Saved Data

All responses saved to:

```
tests/test_data/api_responses/
├── sandbox_requisition_created.json
├── sandbox_details_abc123.json
├── sandbox_balances_abc123.json
└── sandbox_transactions_abc123.json
```

## What You Can Test

### Unlimited Testing

Because this is sandbox:
- ✅ Fetch balances 100 times/day
- ✅ Fetch details 100 times/day
- ✅ Fetch transactions 100 times/day
- ✅ Create multiple requisitions
- ✅ Test error handling
- ✅ Test rate limiting code (it won't actually block)

### Realistic Data

Sandbox returns:
- Real-looking IBANs
- Multiple balance types
- Transaction history
- Pending transactions
- Proper response structures

### Testing Scenarios

You can test:

1. **New Connection**
   ```powershell
   uv run python tests/connect_sandbox.py
   # Create new requisition
   ```

2. **Expired Requisition**
   - Wait for requisition to expire
   - Test renewal flow

3. **Multiple Accounts**
   - Sandbox provides 2-3 accounts
   - Test multi-account handling

4. **Data Updates**
   - Run script multiple times
   - See how data changes (or stays consistent)

## Integrating with Home Assistant

After sandbox testing succeeds, you know:
- ✅ Your credentials work
- ✅ OAuth flow works
- ✅ Data fetching works
- ✅ Rate limiting is configured correctly

Then deploy to Home Assistant with confidence!

## Troubleshooting

### "No linked accounts found"

After authorization, if status is not `LN`:
- Wait a few seconds
- Run the script again
- Requisition should now be linked

### Authorization fails

- Check your credentials in `.env`
- Make sure you completed the full flow
- Try creating a new requisition

### No data returned

- Requisition might be expired (status `EX`)
- Create a new one:
  ```powershell
  uv run python tests/connect_sandbox.py
  # Answer 'n' to create new
  ```

## Comparing to Real Accounts

| Feature | Sandbox | Real Accounts |
|---------|---------|---------------|
| Rate limits | None | 2-4/day |
| Data | Fake | Real |
| Authorization | Instant | Bank-dependent |
| Cost | Free | Free (but limited) |
| Testing | Unlimited | Dangerous |

## Next Steps

After successful sandbox testing:

1. ✅ You've verified the integration works
2. ✅ You understand the OAuth flow
3. ✅ You've seen the data structure
4. Ready to deploy to Home Assistant!
5. Ready to connect real banks!

## Clean Up

Sandbox requisitions don't count against any limits, but if you want to clean up:

1. List all requisitions
2. Delete old sandbox ones via GoCardless dashboard
3. Or just leave them - they don't hurt anything

## Summary

**Sandbox Testing = Risk-Free Testing**

- No rate limits
- No real data at risk
- Perfect for development
- Realistic enough to trust
- Use it liberally!

```powershell
# Test as many times as you want!
uv run python tests/connect_sandbox.py
```

