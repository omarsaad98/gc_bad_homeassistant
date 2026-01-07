"""Interactive test to connect Sandbox Finance institution."""
from __future__ import annotations

import asyncio
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
from tests.conftest import save_api_response


async def main():
    """Connect to Sandbox Finance and test data retrieval."""
    print("=" * 70)
    print("GoCardless Sandbox Connection Test")
    print("=" * 70)
    
    # Get credentials
    secret_id = os.getenv("GCD_SECRET_ID")
    secret_key = os.getenv("GCD_SECRET_KEY")
    
    if not secret_id or not secret_key:
        print("\n[ERROR] Missing credentials in .env file!")
        return
    
    print(f"\n[OK] Credentials loaded")
    
    # Create HA instance and API client
    hass = HomeAssistant("/tmp")
    await hass.async_start()
    
    try:
        client = GoCardlessAPIClient(hass, secret_id, secret_key)
        print("[OK] API Client created")
        
        # Check existing requisitions
        print("\n" + "-" * 70)
        print("Step 1: Checking Existing Requisitions")
        print("-" * 70)
        
        requisitions = await client.get_requisitions()
        
        # Find sandbox requisitions
        sandbox_reqs = [r for r in requisitions 
                       if r.get("institution_id") == "SANDBOXFINANCE_SFIN0000"]
        
        linked_sandbox = [r for r in sandbox_reqs if r.get("status") == "LN"]
        
        print(f"Total requisitions: {len(requisitions)}")
        print(f"Sandbox requisitions: {len(sandbox_reqs)}")
        print(f"Linked sandbox requisitions: {len(linked_sandbox)}")
        
        if linked_sandbox:
            print("\n[OK] You already have linked sandbox accounts!")
            use_existing = input("\nUse existing sandbox connection? (y/n): ").strip().lower()
            
            if use_existing == 'y':
                requisition = linked_sandbox[0]
                print(f"\n[OK] Using existing requisition: {requisition['id']}")
            else:
                print("\n[INFO] Creating new sandbox requisition...")
                requisition = await create_new_requisition(client)
        else:
            print("\n[INFO] No linked sandbox accounts found")
            print("[INFO] Creating new sandbox requisition...")
            requisition = await create_new_requisition(client)
        
        if not requisition:
            print("\n[ERROR] Failed to get or create requisition")
            return
        
        # If requisition is not linked, show authorization link
        if requisition.get("status") != "LN":
            print("\n" + "-" * 70)
            print("Step 2: Authorization Required")
            print("-" * 70)
            
            auth_link = requisition.get("link")
            print(f"\n[ACTION REQUIRED]")
            print(f"Open this link in your browser to authorize:")
            print(f"\n  {auth_link}\n")
            print("After authorizing, press Enter to continue...")
            input()
            
            # Check if now linked
            requisition = await client.get_requisition(requisition["id"])
            
            if requisition.get("status") == "LN":
                print("[OK] Authorization successful!")
            else:
                print(f"[WARN] Status is '{requisition.get('status')}', not 'LN' yet")
                print("      The authorization may still be processing")
                return
        else:
            print("\n[OK] Requisition already linked")
        
        # Get account IDs
        account_ids = requisition.get("accounts", [])
        print(f"\n[OK] Found {len(account_ids)} accounts in requisition")
        
        # Test fetching data from sandbox accounts
        print("\n" + "-" * 70)
        print("Step 3: Fetching Sandbox Account Data")
        print("-" * 70)
        
        for i, account_id in enumerate(account_ids, 1):
            print(f"\n--- Account {i}/{len(account_ids)} ---")
            print(f"Account ID: {account_id}")
            
            # Fetch details
            print("\nFetching details...")
            details = await client.get_account_details(account_id, max_per_day=100)
            
            if details:
                save_api_response(f"sandbox_details_{account_id}", details)
                
                account_info = details.get("account", {})
                print(f"  [OK] IBAN: {account_info.get('iban', 'N/A')}")
                print(f"  [OK] Name: {account_info.get('name', 'N/A')}")
                print(f"  [OK] Currency: {account_info.get('currency', 'N/A')}")
                print(f"  [OK] Status: {account_info.get('status', 'N/A')}")
            else:
                print("  [ERROR] Could not fetch details")
            
            # Fetch balances
            print("\nFetching balances...")
            balances = await client.get_account_balances(account_id, max_per_day=100)
            
            if balances:
                save_api_response(f"sandbox_balances_{account_id}", balances)
                
                balance_list = balances.get("balances", [])
                if balance_list:
                    print(f"  [OK] Found {len(balance_list)} balance(s):")
                    for balance in balance_list:
                        amount_info = balance.get("balanceAmount", {})
                        balance_type = balance.get("balanceType", 'Unknown')
                        amount = amount_info.get("amount", "N/A")
                        currency = amount_info.get("currency", "N/A")
                        print(f"       {balance_type}: {amount} {currency}")
                else:
                    print("  [WARN] No balances found")
            else:
                print("  [ERROR] Could not fetch balances")
            
            # Fetch transactions
            print("\nFetching transactions...")
            transactions = await client.get_account_transactions(account_id, max_per_day=100)
            
            if transactions:
                save_api_response(f"sandbox_transactions_{account_id}", transactions)
                
                booked = transactions.get("transactions", {}).get("booked", [])
                pending = transactions.get("transactions", {}).get("pending", [])
                
                print(f"  [OK] Booked transactions: {len(booked)}")
                print(f"  [OK] Pending transactions: {len(pending)}")
                
                if booked:
                    print("\n  Recent transactions:")
                    for tx in booked[:3]:  # Show first 3
                        amount_info = tx.get("transactionAmount", {})
                        amount = amount_info.get("amount", "N/A")
                        currency = amount_info.get("currency", "N/A")
                        info = tx.get("remittanceInformationUnstructured", "N/A")
                        print(f"    - {amount} {currency}: {info[:40]}")
            else:
                print("  [ERROR] Could not fetch transactions")
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print(f"[OK] Sandbox requisition: {requisition['id']}")
        print(f"[OK] Status: {requisition['status']}")
        print(f"[OK] Accounts tested: {len(account_ids)}")
        print(f"\n[INFO] All responses saved to: tests/test_data/api_responses/")
        print(f"[INFO] These are SANDBOX accounts - safe to test unlimited times!")
        print("=" * 70)
        
    finally:
        await hass.async_stop()


async def create_new_requisition(client: GoCardlessAPIClient) -> dict | None:
    """Create a new sandbox requisition."""
    print("\n" + "-" * 70)
    print("Creating New Sandbox Requisition")
    print("-" * 70)
    
    # Use a simple redirect URL
    # In production, this would be your Home Assistant URL
    redirect_url = "https://www.google.com"  # Placeholder for testing
    
    print(f"Institution: SANDBOXFINANCE_SFIN0000")
    print(f"Redirect URL: {redirect_url}")
    
    requisition = await client.create_requisition(
        institution_id="SANDBOXFINANCE_SFIN0000",
        redirect_url=redirect_url,
        reference=f"sandbox_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    
    if requisition:
        print(f"\n[OK] Requisition created successfully!")
        print(f"     ID: {requisition.get('id')}")
        print(f"     Status: {requisition.get('status')}")
        save_api_response("sandbox_requisition_created", requisition)
        return requisition
    else:
        print("\n[ERROR] Failed to create requisition")
        return None


if __name__ == "__main__":
    print("\nThis test will:")
    print("  1. Check for existing sandbox connections")
    print("  2. Create a new one if needed")
    print("  3. Guide you through authorization")
    print("  4. Fetch and display all account data")
    print("  5. Save responses for review")
    print("\n[SAFE] This uses SANDBOX accounts - no rate limits apply!")
    print()
    
    proceed = input("Proceed? (y/n): ").strip().lower()
    if proceed == 'y':
        asyncio.run(main())
    else:
        print("\nTest cancelled.")

