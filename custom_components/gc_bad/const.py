"""Constants for the GoCardless Bank Account Data integration."""
from datetime import timedelta

DOMAIN = "gc_bad"
CONF_SECRET_ID = "secret_id"
CONF_SECRET_KEY = "secret_key"

# API endpoints
API_BASE_URL = "https://bankaccountdata.gocardless.com"

# Rate limits (per day per account per scope)
# GoCardless actual limits: 10/day (reducing to 4/day soon)
# We use 25% buffer for safety
RATE_LIMIT_BALANCES = 1  # 2/day - 25% buffer = 1.5 → 1 per day
RATE_LIMIT_DETAILS = 1   # 2/day - 25% buffer = 1.5 → 1 per day
RATE_LIMIT_TRANSACTIONS = 3  # 4/day - 25% buffer = 3 per day

# Update intervals based on rate limits with buffer
UPDATE_INTERVAL_BALANCES = timedelta(hours=24)  # Once per day (safe with 1/day limit)
UPDATE_INTERVAL_DETAILS = timedelta(hours=24)   # Once per day (safe with 1/day limit)
UPDATE_INTERVAL_TRANSACTIONS = timedelta(hours=8)  # 3 times per day
UPDATE_INTERVAL_REQUISITIONS = timedelta(minutes=30)  # More frequent for list updates

# Scopes
SCOPE_BALANCES = "balances"
SCOPE_DETAILS = "details"
SCOPE_TRANSACTIONS = "transactions"

# Storage keys
STORAGE_KEY = f"{DOMAIN}_storage"
STORAGE_VERSION = 1
STORAGE_KEY_TOKENS = "tokens"
STORAGE_KEY_RATE_LIMITS = "rate_limits"

