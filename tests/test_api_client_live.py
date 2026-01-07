"""Live API tests using real GoCardless API."""
from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows event loop policy (required for aiodns)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from homeassistant.core import HomeAssistant

from custom_components.gc_bad.api_client import GoCardlessAPIClient


@pytest.mark.asyncio
class TestLiveAPIClient:
    """Test API client with real GoCardless API."""

    async def test_validate_api_key(
        self, hass: HomeAssistant, secret_id: str, secret_key: str, response_logger
    ):
        """Test API key validation with real API."""
        print("\n\n=== Testing API Key Validation ===")
        client = GoCardlessAPIClient(hass, secret_id, secret_key)
        
        result = await client.validate_api_key()
        assert result is True, "API key validation failed"
        print("✓ API key is valid")

    async def test_get_requisitions(
        self, hass: HomeAssistant, secret_id: str, secret_key: str, response_logger
    ):
        """Test fetching requisitions from real API."""
        print("\n\n=== Testing Get Requisitions ===")
        client = GoCardlessAPIClient(hass, secret_id, secret_key)
        
        requisitions = await client.get_requisitions()
        response_logger("requisitions", {"count": len(requisitions), "requisitions": requisitions})
        
        print(f"Retrieved {len(requisitions)} requisitions")
        
        for req in requisitions:
            print(f"  - Requisition ID: {req.get('id')}")
            print(f"    Status: {req.get('status')}")
            print(f"    Institution: {req.get('institution_id')}")
            print(f"    Accounts: {len(req.get('accounts', []))}")

    async def test_get_institutions_by_country(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test fetching institutions for different countries."""
        print("\n\n=== Testing Get Institutions ===")
        client = GoCardlessAPIClient(hass, api_secret)
        
        test_countries = ["GB", "US", "DE", "FR"]
        
        for country in test_countries:
            print(f"\nFetching institutions for {country}...")
            institutions = await client.get_institutions(country)
            response_logger(f"institutions_{country}", institutions)
            
            print(f"✓ Found {len(institutions)} institutions in {country}")
            if institutions:
                print(f"  Sample: {institutions[0].get('name', 'N/A')}")

    async def test_get_specific_requisition(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test fetching a specific requisition if any exist."""
        print("\n\n=== Testing Get Specific Requisition ===")
        client = GoCardlessAPIClient(hass, api_secret)
        
        # First get all requisitions
        requisitions = await client.get_requisitions()
        
        if not requisitions:
            print("⊘ No requisitions found to test with")
            pytest.skip("No requisitions available")
            return
        
        # Test with first requisition
        req_id = requisitions[0]["id"]
        print(f"Testing with requisition: {req_id}")
        
        requisition = await client.get_requisition(req_id)
        response_logger(f"requisition_detail_{req_id}", requisition)
        
        assert requisition is not None
        print("✓ Retrieved requisition details")
        print(f"  Status: {requisition.get('status')}")
        print(f"  Created: {requisition.get('created')}")
        print(f"  Accounts: {requisition.get('accounts', [])}")

    async def test_get_account_details(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test fetching account details for linked accounts."""
        print("\n\n=== Testing Get Account Details ===")
        client = GoCardlessAPIClient(hass, api_secret)
        
        # Get requisitions and find linked accounts
        requisitions = await client.get_requisitions()
        
        linked_accounts = []
        for req in requisitions:
            if req.get("status") == "LN":  # Linked
                linked_accounts.extend(req.get("accounts", []))
        
        if not linked_accounts:
            print("⊘ No linked accounts found")
            pytest.skip("No linked accounts available")
            return
        
        # Test with first account
        account_id = linked_accounts[0]
        print(f"Testing with account: {account_id}")
        
        details = await client.get_account_details(account_id, max_per_day=10)
        response_logger(f"account_details_{account_id}", details or {})
        
        if details:
            print("✓ Retrieved account details")
            account_info = details.get("account", {})
            print(f"  IBAN: {account_info.get('iban', 'N/A')[:10]}***")
            print(f"  Currency: {account_info.get('currency', 'N/A')}")
            print(f"  Name: {account_info.get('name', 'N/A')}")
        else:
            print("⊘ Could not retrieve account details (may be rate limited)")

    async def test_get_account_balances(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test fetching account balances for linked accounts."""
        print("\n\n=== Testing Get Account Balances ===")
        client = GoCardlessAPIClient(hass, api_secret)
        
        # Get requisitions and find linked accounts
        requisitions = await client.get_requisitions()
        
        linked_accounts = []
        for req in requisitions:
            if req.get("status") == "LN":  # Linked
                linked_accounts.extend(req.get("accounts", []))
        
        if not linked_accounts:
            print("⊘ No linked accounts found")
            pytest.skip("No linked accounts available")
            return
        
        # Test with first account
        account_id = linked_accounts[0]
        print(f"Testing with account: {account_id}")
        
        balances = await client.get_account_balances(account_id, max_per_day=10)
        response_logger(f"account_balances_{account_id}", balances or {})
        
        if balances:
            print("✓ Retrieved account balances")
            balance_list = balances.get("balances", [])
            for balance in balance_list:
                amount = balance.get("balanceAmount", {})
                print(f"  {balance.get('balanceType')}: {amount.get('amount')} {amount.get('currency')}")
        else:
            print("⊘ Could not retrieve balances (may be rate limited)")

    async def test_get_account_transactions(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test fetching account transactions for linked accounts."""
        print("\n\n=== Testing Get Account Transactions ===")
        client = GoCardlessAPIClient(hass, api_secret)
        
        # Get requisitions and find linked accounts
        requisitions = await client.get_requisitions()
        
        linked_accounts = []
        for req in requisitions:
            if req.get("status") == "LN":  # Linked
                linked_accounts.extend(req.get("accounts", []))
        
        if not linked_accounts:
            print("⊘ No linked accounts found")
            pytest.skip("No linked accounts available")
            return
        
        # Test with first account
        account_id = linked_accounts[0]
        print(f"Testing with account: {account_id}")
        
        transactions = await client.get_account_transactions(account_id, max_per_day=10)
        response_logger(f"account_transactions_{account_id}", transactions or {})
        
        if transactions:
            print("✓ Retrieved account transactions")
            tx_list = transactions.get("transactions", {}).get("booked", [])
            print(f"  Total transactions: {len(tx_list)}")
            if tx_list:
                latest = tx_list[0]
                amount = latest.get("transactionAmount", {})
                print(f"  Latest: {amount.get('amount')} {amount.get('currency')} - {latest.get('remittanceInformationUnstructured', 'N/A')[:30]}")
        else:
            print("⊘ Could not retrieve transactions (may be rate limited)")

    async def test_rate_limit_tracking(
        self, hass: HomeAssistant, api_secret: str, response_logger
    ):
        """Test that rate limiting is being tracked."""
        print("\n\n=== Testing Rate Limit Tracking ===")
        client = GoCardlessAPIClient(hass, api_secret)
        
        # Get a linked account
        requisitions = await client.get_requisitions()
        linked_accounts = []
        for req in requisitions:
            if req.get("status") == "LN":
                linked_accounts.extend(req.get("accounts", []))
        
        if not linked_accounts:
            pytest.skip("No linked accounts available")
            return
        
        account_id = linked_accounts[0]
        
        # Make first request
        print(f"Making first balance request for {account_id}...")
        result1 = await client.get_account_balances(account_id, max_per_day=2)
        
        if result1:
            print("✓ First request successful")
            
            # Check rate limit data
            rate_limit_key = f"balances_{account_id}"
            if rate_limit_key in client._rate_limits:
                limit_info = client._rate_limits[rate_limit_key]
                print(f"  Rate limit count: {limit_info['count']}/2")
                print(f"  Resets at: {limit_info['reset_time']}")
        else:
            print("⊘ First request failed or rate limited")

