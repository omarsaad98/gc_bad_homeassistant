"""Check what rate limit headers GoCardless API actually returns."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows event loop policy (required for aiodns)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp


async def main():
    """Check GoCardless API response headers."""
    print("=" * 70)
    print("GoCardless API Response Headers Inspection")
    print("=" * 70)
    
    # Get credentials
    secret_id = os.getenv("GCD_SECRET_ID")
    secret_key = os.getenv("GCD_SECRET_KEY")
    
    if not secret_id or not secret_key:
        print("\n[ERROR] Missing credentials in .env file!")
        return
    
    base_url = "https://bankaccountdata.gocardless.com"
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Get access token
        print("\n" + "-" * 70)
        print("Step 1: Getting Access Token")
        print("-" * 70)
        
        async with session.post(
            f"{base_url}/api/v2/token/new/",
            json={"secret_id": secret_id, "secret_key": secret_key},
        ) as response:
            print(f"Status: {response.status}")
            print(f"\nAll Response Headers:")
            for header, value in response.headers.items():
                print(f"  {header}: {value}")
            
            data = await response.json()
            access_token = data["access"]
            print(f"\n[OK] Access token obtained")
        
        # Step 2: Test different endpoints
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        endpoints_to_test = [
            ("Requisitions", "/api/v2/requisitions/"),
            ("Institutions (GB)", "/api/v2/institutions/?country=GB"),
        ]
        
        # Get a linked account ID if available
        async with session.get(
            f"{base_url}/api/v2/requisitions/",
            headers=headers,
        ) as response:
            reqs_data = await response.json()
            requisitions = reqs_data.get("results", [])
            
            linked_accounts = []
            for req in requisitions:
                if req.get("status") == "LN":
                    linked_accounts.extend(req.get("accounts", []))
            
            if linked_accounts:
                account_id = linked_accounts[0]
                endpoints_to_test.extend([
                    ("Account Details", f"/api/v2/accounts/{account_id}/details/"),
                    ("Account Balances", f"/api/v2/accounts/{account_id}/balances/"),
                    ("Account Transactions", f"/api/v2/accounts/{account_id}/transactions/"),
                ])
                print(f"[OK] Testing with account: {account_id}")
        
        # Test each endpoint
        for name, endpoint in endpoints_to_test:
            print("\n" + "-" * 70)
            print(f"Testing: {name}")
            print(f"Endpoint: {endpoint}")
            print("-" * 70)
            
            try:
                async with session.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                ) as response:
                    print(f"Status: {response.status}")
                    
                    # Check for rate limit headers (various common names)
                    rate_limit_headers = [
                        "X-RateLimit-Limit",
                        "X-RateLimit-Remaining",
                        "X-RateLimit-Reset",
                        "X-Rate-Limit-Limit",
                        "X-Rate-Limit-Remaining",
                        "X-Rate-Limit-Reset",
                        "RateLimit-Limit",
                        "RateLimit-Remaining",
                        "RateLimit-Reset",
                        "Retry-After",
                    ]
                    
                    found_rate_headers = {}
                    for header_name in rate_limit_headers:
                        if header_name in response.headers:
                            found_rate_headers[header_name] = response.headers[header_name]
                    
                    if found_rate_headers:
                        print("\n[FOUND] Rate Limit Headers:")
                        for header, value in found_rate_headers.items():
                            print(f"  {header}: {value}")
                    else:
                        print("\n[INFO] No rate limit headers found")
                    
                    print("\nAll Response Headers:")
                    for header, value in response.headers.items():
                        print(f"  {header}: {value}")
                    
                    # Pause between requests
                    await asyncio.sleep(1)
                    
            except Exception as err:
                print(f"\n[ERROR] Request failed: {err}")
        
        print("\n" + "=" * 70)
        print("Header Inspection Complete")
        print("=" * 70)
        print("\n[INFO] Check above for rate limit headers")
        print("[INFO] Common header names:")
        print("  - X-RateLimit-Limit")
        print("  - X-RateLimit-Remaining")
        print("  - X-RateLimit-Reset")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

