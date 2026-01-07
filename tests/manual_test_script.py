"""Manual test script for interactive API testing."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows event loop policy (required for aiodns)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from homeassistant.core import HomeAssistant

from custom_components.gc_bad.api_client import GoCardlessAPIClient
from tests.conftest import save_api_response, save_tokens


async def main():
    """Run manual API tests."""
    print("=" * 70)
    print("GoCardless API Manual Test Script")
    print("=" * 70)
    
    # Get API credentials
    secret_id = os.getenv("GCD_SECRET_ID")
    secret_key = os.getenv("GCD_SECRET_KEY")
    
    if not secret_id or not secret_key:
        print("\n[ERROR] Missing credentials!")
        print("        GCD_SECRET_ID:", "SET" if secret_id else "NOT SET")
        print("        GCD_SECRET_KEY:", "SET" if secret_key else "NOT SET")
        print("\n        Solution:")
        print("        1. Copy .env.example to .env")
        print("        2. Edit .env and add your credentials")
        print("        3. Run the test again")
        print("\n        Or set environment variables:")
        print("        $env:GCD_SECRET_ID='your-secret-id-here'")
        print("        $env:GCD_SECRET_KEY='your-secret-key-here'")
        return
    
    print(f"\n[OK] Credentials loaded")
    print(f"     Secret ID length: {len(secret_id)}")
    print(f"     Secret Key length: {len(secret_key)}")
    
    # Create a minimal HomeAssistant instance for testing
    hass = HomeAssistant("/tmp")
    await hass.async_start()
    
    try:
        # Create API client
        client = GoCardlessAPIClient(hass, secret_id, secret_key)
        print("\n[OK] API Client created")
        
        # Test 1: Validate API key
        print("\n" + "-" * 70)
        print("TEST 1: Validating API Key")
        print("-" * 70)
        is_valid = await client.validate_api_key()
        if is_valid:
            print("[OK] API key is VALID")
        else:
            print("[ERROR] API key is INVALID")
            return
        
        # Test 2: Get requisitions
        print("\n" + "-" * 70)
        print("TEST 2: Fetching Requisitions")
        print("-" * 70)
        requisitions = await client.get_requisitions()
        print(f"[OK] Found {len(requisitions)} requisitions")
        
        save_api_response("manual_requisitions", {
            "count": len(requisitions),
            "requisitions": requisitions
        })
        
        for i, req in enumerate(requisitions, 1):
            print(f"\n  Requisition {i}:")
            print(f"    ID: {req.get('id')}")
            print(f"    Status: {req.get('status')}")
            print(f"    Institution: {req.get('institution_id')}")
            print(f"    Created: {req.get('created')}")
            print(f"    Accounts: {len(req.get('accounts', []))}")
            
            for account_id in req.get('accounts', []):
                print(f"      - {account_id}")
        
        # Test 3: Get institutions for a few countries
        print("\n" + "-" * 70)
        print("TEST 3: Fetching Institutions by Country")
        print("-" * 70)
        test_countries = ["GB", "US", "DE"]
        
        for country in test_countries:
            print(f"\n  {country}:")
            institutions = await client.get_institutions(country)
            print(f"    [OK] Found {len(institutions)} institutions")
            
            save_api_response(f"manual_institutions_{country}", institutions)
            
            # Show first 3
            for inst in institutions[:3]:
                print(f"      - {inst.get('name')} (ID: {inst.get('id')})")
            
            if len(institutions) > 3:
                print(f"      ... and {len(institutions) - 3} more")
        
        # Test 4: Get account details (ONLY for sandbox to avoid rate limits)
        print("\n" + "-" * 70)
        print("TEST 4: Fetching Account Details (Sandbox Only)")
        print("-" * 70)
        
        # Find sandbox accounts only to avoid rate limits
        sandbox_accounts = []
        for req in requisitions:
            if req.get("institution_id") == "SANDBOXFINANCE_SFIN0000":
                if req.get("status") == "LN":
                    sandbox_accounts.extend(req.get("accounts", []))
        
        linked_accounts = []
        for req in requisitions:
            if req.get("status") == "LN":
                linked_accounts.extend(req.get("accounts", []))
        
        if linked_accounts:
            print(f"[OK] Found {len(linked_accounts)} linked accounts total")
            if sandbox_accounts:
                print(f"[OK] Testing with {len(sandbox_accounts)} sandbox accounts (safe from rate limits)")
            else:
                print(f"[WARN] No sandbox accounts found - skipping to avoid rate limits on real accounts")
        
        # Only fetch details for sandbox accounts
        if sandbox_accounts:
            for account_id in sandbox_accounts:
                print(f"\n  Sandbox Account: {account_id}")
                
                # Safe to fetch sandbox account details (no real rate limits)
                details = await client.get_account_details(account_id, max_per_day=10)
                if details:
                    save_api_response(f"manual_details_{account_id}", details)
                    
                    account_info = details.get("account", {})
                    iban = account_info.get("iban", "N/A")
                    masked_iban = iban[:6] + "****" + iban[-4:] if len(iban) > 10 else "N/A"
                    
                    print(f"    IBAN: {masked_iban}")
                    print(f"    Currency: {account_info.get('currency', 'N/A')}")
                    print(f"    Name: {account_info.get('name', 'N/A')}")
                    print(f"    Status: {account_info.get('status', 'N/A')}")
                else:
                    print(f"    [WARN] Could not fetch details")
        elif not linked_accounts:
            print("  [WARN] No linked accounts found")
        else:
            print("  [INFO] Skipping real account details to preserve rate limits")
            print("        Use sandbox accounts (SANDBOXFINANCE_SFIN0000) for testing")
        
        # Test 5: Get balances (ONLY for sandbox to avoid rate limits)
        print("\n" + "-" * 70)
        print("TEST 5: Fetching Account Balances (Sandbox Only)")
        print("-" * 70)
        
        if sandbox_accounts:
            for account_id in sandbox_accounts:
                print(f"\n  Sandbox Account: {account_id}")
                
                # Safe to fetch sandbox balances (no real rate limits)
                balances = await client.get_account_balances(account_id, max_per_day=10)
                if balances:
                    save_api_response(f"manual_balances_{account_id}", balances)
                    
                    balance_list = balances.get("balances", [])
                    for balance in balance_list:
                        amount_info = balance.get("balanceAmount", {})
                        print(f"    {balance.get('balanceType', 'Unknown')}: "
                              f"{amount_info.get('amount', 'N/A')} "
                              f"{amount_info.get('currency', 'N/A')}")
                else:
                    print(f"    [WARN] Could not fetch balances")
        elif linked_accounts and not sandbox_accounts:
            print("  [INFO] Skipping real account balances to preserve rate limits")
            print("        Real accounts limited to 2 requests/day!")
            print("        Use sandbox accounts (SANDBOXFINANCE_SFIN0000) for testing")
        
        # Test 6: Rate limit info
        print("\n" + "-" * 70)
        print("TEST 6: Rate Limit Information")
        print("-" * 70)
        
        if client._rate_limits:
            print("\n  Current rate limit tracking:")
            for key, info in client._rate_limits.items():
                print(f"    {key}:")
                print(f"      Count: {info['count']}")
                print(f"      Resets: {info['reset_time']}")
        else:
            print("  No rate limits tracked yet")
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"[OK] API Key: Valid")
        print(f"[OK] Requisitions: {len(requisitions)}")
        print(f"[OK] Linked Accounts: {len(linked_accounts)}")
        if sandbox_accounts:
            print(f"[OK] Sandbox Accounts Tested: {len(sandbox_accounts)}")
        print(f"\nAll API responses saved to: tests/test_data/api_responses/")
        print("\n[IMPORTANT] Rate Limit Protection:")
        print("  - Real accounts: 2 requests/day for balances/details")
        print("  - Tests only fetch from sandbox accounts")
        print("  - Use SANDBOXFINANCE_SFIN0000 for safe testing")
        print("=" * 70)
        
    finally:
        await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())

