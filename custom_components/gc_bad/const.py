"""Constants for the GoCardless Bank Account Data integration."""
from datetime import timedelta

DOMAIN = "gc_bad"
CONF_API_SECRET = "api_secret"

# API endpoints
API_BASE_URL = "https://bankaccountdata.gocardless.com"

# Rate limits (per day per account per scope)
# Starting value is 10, reducing to 4 in future
RATE_LIMIT_BALANCES = 2  # Conservative: 2 per day for balances
RATE_LIMIT_DETAILS = 2   # Conservative: 2 per day for details
RATE_LIMIT_TRANSACTIONS = 4  # 4 per day for transactions

# Update intervals based on rate limits
UPDATE_INTERVAL_BALANCES = timedelta(hours=12)  # Twice per day
UPDATE_INTERVAL_DETAILS = timedelta(hours=12)   # Twice per day
UPDATE_INTERVAL_TRANSACTIONS = timedelta(hours=6)  # 4 times per day
UPDATE_INTERVAL_REQUISITIONS = timedelta(minutes=30)  # More frequent for list updates

# Scopes
SCOPE_BALANCES = "balances"
SCOPE_DETAILS = "details"
SCOPE_TRANSACTIONS = "transactions"

# Storage keys
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1

